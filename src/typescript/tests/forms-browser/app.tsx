import {
  rankWith,
  uiTypeIs,
  type ControlProps,
  type ValidationMode
} from "@jsonforms/core";
import { withJsonFormsControlProps } from "@jsonforms/react";
import { createRoot } from "react-dom/client";
import { useMemo, useState, type ReactNode } from "react";
import { OrbyssJsonForms } from "@orbyss-io/forms-react";
import type { JsonValue, RuntimeValidationIssue } from "@orbyss-io/forms-contracts";
import { schema } from "./schema.mjs";
import { validate as validateGenerated } from "orbyss-forms:validator";

interface GeneratedError {
  readonly instancePath: string;
  readonly keyword: string;
  readonly message?: string;
  readonly params?: { readonly missingProperty?: string };
}

const generated = validateGenerated as typeof validateGenerated & { errors?: readonly GeneratedError[] | null };
const uiSchema = { type: "Control", scope: "#/properties/name", label: "Name", i18n: "fields.name" };

function validate(data: JsonValue): readonly RuntimeValidationIssue[] {
  if (generated(data)) return [];
  return (generated.errors ?? []).map(error => ({
    path: error.instancePath,
    keyword: error.keyword,
    message: error.message ?? error.keyword,
    ...(error.params?.missingProperty === undefined ? {} : { property: error.params.missingProperty })
  }));
}

function ConsumerTextControl(props: ControlProps): ReactNode {
  if (!props.visible) return null;
  const errorId = props.errors.length === 0 ? undefined : `${props.id}-error`;
  return <div className="consumer-field" data-control-path={props.path}>
    <label htmlFor={props.id}>{props.label}{props.required ? " *" : ""}</label>
    <input
      aria-describedby={errorId}
      aria-invalid={errorId === undefined ? undefined : true}
      disabled={!props.enabled}
      id={props.id}
      onChange={event => props.handleChange(props.path, event.currentTarget.value)}
      required={props.required}
      value={typeof props.data === "string" ? props.data : ""}
    />
    {errorId === undefined ? null : <p className="consumer-error" id={errorId} role="alert">{props.errors}</p>}
  </div>;
}

const ConsumerTextRenderer = withJsonFormsControlProps(ConsumerTextControl);
const renderers = [{ tester: rankWith(1000, uiTypeIs("Control")), renderer: ConsumerTextRenderer }];

function App(): ReactNode {
  const [locale, setLocale] = useState<"en" | "ar">("en");
  const [data, setData] = useState<JsonValue>({});
  const [validationMode, setValidationMode] = useState<ValidationMode>("ValidateAndHide");
  const [result, setResult] = useState("");
  const runtime = useMemo(() => ({
    schema,
    uiSchema,
    validate,
    translate: (key: string, fallback: string) => key === "fields.name"
      ? locale === "ar" ? "الاسم" : "Name"
      : fallback
  }), [locale]);
  const submit = () => {
    setValidationMode("ValidateAndShow");
    setResult(validate(data).length === 0 ? "submitted" : "validation");
  };
  return <main>
    <header className="fixture-header">
      <div>
        <p className="fixture-eyebrow">Orbyss Forms engine</p>
        <h1>Consumer-rendered form acceptance</h1>
      </div>
      <button onClick={() => {
        setLocale(value => value === "en" ? "ar" : "en");
        document.documentElement.dir = locale === "en" ? "rtl" : "ltr";
      }} type="button">{locale === "en" ? "العربية" : "English"}</button>
    </header>
    <section className="consumer-form">
      <OrbyssJsonForms
        data={data}
        onChange={next => setData(next)}
        renderers={renderers}
        runtime={runtime}
        validationMode={validationMode}
      />
      <button className="consumer-submit" onClick={submit} type="button">Submit</button>
    </section>
    <p aria-live="polite" className="fixture-action-result">{result}</p>
    <output aria-hidden="true" className="fixture-form-data" hidden>{JSON.stringify(data)}</output>
  </main>;
}

const root = document.getElementById("root");
if (root === null) throw new Error("Fixture root is missing.");
createRoot(root).render(<App />);
