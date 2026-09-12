import { rankWith, uiTypeIs, type ControlProps, type Layout, type LayoutProps, type JsonFormsRendererRegistryEntry } from "@jsonforms/core";
import { JsonFormsDispatch, withJsonFormsControlProps, withJsonFormsLayoutProps } from "@jsonforms/react";
import { createRoot } from "react-dom/client";
import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { OrbyssJsonForms, useOrbyssFormsRuntime } from "@orbyss-io/forms-react";
import { admitFormRelease, createJsonFormsTranslator, jsonFormsValidationErrorsToIssues, prepareJsonFormsRuntime } from "@orbyss-io/forms-jsonforms-runtime";
import { FormActionRegistry, RendererRegistry } from "@orbyss-io/forms-renderer-registry";
import { OrbyssActionController, parseOrbyssActionBar } from "@orbyss-io/forms-actions";
import { OrbyssWizardController, parseOrbyssWizard } from "@orbyss-io/forms-wizard";
import type { JsonObject, JsonValue } from "@orbyss-io/forms-contracts";
import { validate as generated, binding } from "orbyss-forms:validator";
import deployment from "orbyss-forms:deployment";

const validate = (data: JsonValue) => generated(data) ? [] : jsonFormsValidationErrorsToIssues(generated.errors ?? []);
const initialData = (): JsonObject => ({ kind: "standard", editable: true, quantity: 1, reference: "DEMO" });
const Journey = createContext({ step: "configure", calculate: () => {}, edit: (_path: string, _value: JsonValue | undefined) => {}, running: false, showErrors: false });

// Application policy for this flat synthetic form. One root update applies the edit and
// branch cleanup atomically, rather than transforming a later debounced notification.
function referenceFieldChange(data: JsonObject, path: string, value: JsonValue | undefined): JsonObject {
  const next: Record<string, JsonValue> = { ...data };
  if (value === undefined) delete next[path]; else next[path] = value;
  if (path === "kind" && value !== data.kind) delete next.detail;
  return next;
}

function ConsumerControl(props: ControlProps): ReactNode {
  const runtime = useOrbyssFormsRuntime()!;
  const journey = useContext(Journey);
  if (!props.visible) return null;
  const errors = journey.showErrors ? props.errors || "" : "";
  const errorId = errors ? `${props.id}-error` : undefined;
  const descriptionKey = (props.schema as JsonObject)["x-description-i18n"];
  const description = typeof descriptionKey === "string" ? runtime.translate(descriptionKey, "") : "";
  const helpId = description ? `${props.id}-help` : undefined;
  const common = { id: props.id, disabled: !props.enabled, "aria-describedby": [helpId, errorId].filter(Boolean).join(" ") || undefined, "aria-invalid": errors ? true as const : undefined };
  const choices = props.schema.oneOf as { const: string; title: string; "x-i18n": string }[] | undefined;
  const update = (value: JsonValue | undefined) => {
    journey.edit(props.path, value);
  };
  return <div className="consumer-field" data-control-path={props.path}>
    <label htmlFor={props.id}>{props.label}{props.required ? " *" : ""}</label>
    {description ? <p className="consumer-help" id={helpId}>{description}</p> : null}
    {choices ? <select {...common} value={String(props.data ?? "")} onChange={event => update(event.target.value)}>
      {choices.map(choice => <option key={choice.const} value={choice.const}>{runtime.translate(choice["x-i18n"], choice.title)}</option>)}
    </select> : props.schema.type === "boolean" ? <input {...common} type="checkbox" checked={props.data === true} onChange={event => update(event.target.checked)} />
      : <input {...common} type={props.schema.type === "integer" || props.schema.type === "number" ? "number" : "text"}
        value={typeof props.data === "string" || typeof props.data === "number" ? props.data : ""}
        readOnly={(props.schema as JsonObject).readOnly === true}
        onChange={event => update(event.target.value === "" ? undefined : event.target.type === "number" ? Number(event.target.value) : event.target.value)} />}
    {errors ? <p className="consumer-error" id={errorId} role="alert">{errors}</p> : null}
  </div>;
}

function ConsumerLayout(props: LayoutProps): ReactNode {
  const journey = useContext(Journey);
  if (!props.visible) return null;
  const elements = (props.uischema as Layout).elements ?? [];
  const selected = props.uischema.type === "Categorization"
    ? elements.filter(element => (element as unknown as JsonObject).id === journey.step) : elements;
  return <div className="consumer-layout">{selected.map((element, index) => <JsonFormsDispatch key={index} schema={props.schema} uischema={element} path={props.path} enabled={props.enabled} {...(props.renderers === undefined ? {} : { renderers: props.renderers })} />)}</div>;
}

function ConsumerActionBar(props: LayoutProps): ReactNode {
  const journey = useContext(Journey);
  const runtime = useOrbyssFormsRuntime()!;
  if (!props.visible) return null;
  return <button className="consumer-submit" type="button" disabled={!props.enabled || journey.running} onClick={journey.calculate}>{runtime.translate("actions.calculate", "")}</button>;
}

const controlRenderer = withJsonFormsControlProps(ConsumerControl);
const layoutRenderer = withJsonFormsLayoutProps(ConsumerLayout);
const actionRenderer = withJsonFormsLayoutProps(ConsumerActionBar);
const rendererEntries: JsonFormsRendererRegistryEntry[] = [
  { tester: rankWith(1000, uiTypeIs("Control")), renderer: controlRenderer },
  ...["VerticalLayout", "HorizontalLayout", "Group", "Category", "Categorization"].map(type => ({ tester: rankWith(1000, uiTypeIs(type)), renderer: layoutRenderer })),
  { tester: rankWith(1000, uiTypeIs("Orbyss.Forms.ActionBar")), renderer: actionRenderer }
];
const registry = new RendererRegistry([
  { componentId: "Orbyss.Forms.Wizard", version: "1.0.0", rank: (ui: JsonObject) => ui.type === "Categorization" ? 1000 : -1, renderer: rendererEntries.find(entry => entry.renderer === layoutRenderer)! },
  { componentId: "Orbyss.Forms.ActionBar", version: "1.0.0", rank: (ui: JsonObject) => ui.type === "Orbyss.Forms.ActionBar" ? 1000 : -1, renderer: rendererEntries.at(-1)! }
]);

async function start(): Promise<void> {
  const admitted = await admitFormRelease(deployment.releaseJson, deployment.localeJson, deployment.manifest, { ...binding, validate });
  const actions = new FormActionRegistry({ "synthetic.calculate": async payload => {
    // Deliberately finishes after cancellation to exercise late-result suppression.
    await new Promise(resolve => setTimeout(resolve, 350));
    return { amount: Number((payload as JsonObject).quantity) * 10 };
  } });
  const prepared = await prepareJsonFormsRuntime(admitted.release, registry, actions, admitted.validate, createJsonFormsTranslator(admitted.translations.en!));
  const wizardDefinition = parseOrbyssWizard(prepared.uiSchema, prepared.translate);
  const actionElement = ((prepared.uiSchema.elements as JsonObject[])[1]!.elements as JsonObject[]).find(element => element.type === "Orbyss.Forms.ActionBar")!;
  const actionDefinition = parseOrbyssActionBar(actionElement, prepared.actions);

  function App(): ReactNode {
    const [locale, setLocale] = useState("en");
    const [data, setData] = useState<JsonObject>(initialData);
    const current = useRef(data);
    const generation = useRef(0);
    const [epoch, setEpoch] = useState(0);
    const [showErrors, setShowErrors] = useState(false);
    const [readOnly, setReadOnly] = useState(false);
    const [result, setResult] = useState("");
    const [amount, setAmount] = useState<JsonValue>();
    const [running, setRunning] = useState(false);
    const [step, setStep] = useState("configure");
    const wizard = useMemo(() => new OrbyssWizardController(wizardDefinition, { onChange: state => setStep(state.currentStepId) }), []);
    const controller = useMemo(() => new OrbyssActionController(actionDefinition, {
      validate: prepared.validate,
      dispatch: (id, payload, signal) => prepared.dispatchAction(id, payload, { signal }),
      onChange: state => setRunning(state.runningActionId !== undefined)
    }), []);
    const dictionary = admitted.translations[locale]!;
    const t = (key: string) => dictionary[key] ?? "";
    const runtime = useMemo(() => ({ ...prepared, translate: (key: string, fallback: string) => {
      const genericError = key.includes(".error.") ? "error." + key.split(".error.")[1] : key;
      return dictionary[key] ?? dictionary[genericError] ?? fallback;
    } }), [dictionary]);
    const edit = (path: string, value: JsonValue | undefined) => {
      // Application-owned controls update one authoritative state synchronously. Engine
      // notifications are observations, never a second writer of application data.
      const next = referenceFieldChange(current.current, path, value);
      generation.current++; controller.cancel(); setResult(""); setAmount(undefined);
      current.current = next; setData(next);
    };
    const calculate = async () => {
      const token = ++generation.current;
      setShowErrors(true); setAmount(undefined);
      setResult(prepared.validate(current.current).length ? "validation" : "running");
      const outcome = await controller.invoke("calculate", current.current, { data: current.current });
      if (token !== generation.current) return;
      setResult(outcome.invoked ? "succeeded" : outcome.reason === "validation" ? "validation" : outcome.reason === "cancelled" ? "cancelled" : "failed");
      if (outcome.invoked) setAmount(outcome.value);
    };
    return <main>
      <header className="fixture-header"><h1>{t("app.title")}</h1><label>{t("app.language")}<select aria-label={t("app.language")} value={locale} onChange={event => {
        const next = event.target.value; setLocale(next); document.documentElement.lang = next; document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
      }}>{Object.keys(admitted.translations).map(code => <option key={code} value={code}>{({ en: "English", nl: "Nederlands", de: "Deutsch", ar: "العربية" } as Record<string, string>)[code]}</option>)}</select></label></header>
      <h2>{t("steps." + step)}</h2>
      <section className="consumer-form">
        <label><input data-testid="review-lock" type="checkbox" checked={readOnly} onChange={event => setReadOnly(event.target.checked)} />{t("app.readonly")}</label>
        <Journey.Provider value={{ step, calculate: () => { void calculate(); }, edit, running, showErrors }}>
          <OrbyssJsonForms key={epoch} data={data} renderers={rendererEntries} runtime={runtime} readonly={readOnly} validationMode="ValidateAndShow" />
        </Journey.Provider>
        <nav className="fixture-navigation">
          <button type="button" data-testid="back" disabled={step === "configure"} onClick={() => wizard.back()}>{t("app.back")}</button>
          <button type="button" data-testid="next" disabled={step === "review"} onClick={() => { void wizard.next(); }}>{t("app.next")}</button>
          <button type="button" data-testid="cancel" disabled={!running} onClick={() => { generation.current++; controller.cancel(); setResult("cancelled"); }}>{t("app.cancel")}</button>
          <button type="button" data-testid="reset" onClick={() => { generation.current++; setEpoch(value => value + 1); controller.cancel(); const value = initialData(); current.current = value; setData(value); setResult(""); setAmount(undefined); setShowErrors(false); setReadOnly(false); wizard.back(); }}>{t("app.reset")}</button>
        </nav>
      </section>
      <p aria-live="polite" className="fixture-action-result" data-status={result}>{result ? t("app." + result) : ""}{amount === undefined ? "" : ` · ${(amount as JsonObject).amount}`}</p>
      <output className="fixture-form-data" hidden>{JSON.stringify(data)}</output>
      <output data-testid="release" hidden>{admitted.release.id.value}</output>
    </main>;
  }
  createRoot(document.getElementById("root")!).render(<App />);
}
void start().catch(error => { console.error(error); document.getElementById("root")!.textContent = "Form unavailable"; });
