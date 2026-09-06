import {
  rankWith,
  uiTypeIs,
  type LayoutProps
} from "@jsonforms/core";
import {
  JsonFormsDispatch,
  withJsonFormsLayoutProps
} from "@jsonforms/react";
import { createRoot } from "react-dom/client";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ProgramKitJsonForms } from "@orbyss/program-kit-forms-react";
import { FormLookupRegistry } from "@orbyss/program-kit-forms-lookups";
import { programKitSearchableSelectRendererEntry } from "@orbyss/program-kit-forms-lookups-react";
import type { FormActionRequirement, JsonValue, RuntimeValidationIssue } from "@orbyss/program-kit-forms-contracts";
import { schema } from "./schema.mjs";
import { validate as validateGenerated } from "program-kit:validator";

interface GeneratedError {
  readonly instancePath: string;
  readonly keyword: string;
  readonly message?: string;
  readonly params?: { readonly missingProperty?: string; readonly additionalProperty?: string };
}

const generated = validateGenerated as typeof validateGenerated & { errors?: readonly GeneratedError[] | null };

const uiSchema = {
  type: "Categorization",
  id: "account-setup",
  options: {
    variant: "program-kit-wizard",
    navigationPolicy: "visited",
    navigationPlacement: "adaptive",
    progressStyle: "progress",
    validateBeforeAdvance: true,
    saveProgress: true,
    deepLink: true
  },
  elements: [
    {
      type: "Category",
      id: "profile",
      label: "Profile",
      i18n: "steps.profile",
      options: { icon: { name: "user", bundle: "lucide" } },
      elements: [
        { type: "Control", id: "name", scope: "#/properties/name", label: "Name", i18n: "fields.name" },
        { type: "Control", id: "notes", scope: "#/properties/notes", label: "Notes", i18n: "fields.notes", options: { multi: true, rows: 4 } },
        { type: "Control", id: "quantity", scope: "#/properties/quantity", label: "Quantity", i18n: "fields.quantity" },
        { type: "Control", id: "updates", scope: "#/properties/updates", label: "Product updates", i18n: "fields.updates" },
        { type: "Control", id: "role", scope: "#/properties/role", label: "Role", i18n: "fields.role", options: { enumLabels: ["Reader", "Writer"] } },
        { type: "Control", id: "channels", scope: "#/properties/channels", label: "Channels", i18n: "fields.channels", options: { enumLabels: ["Email", "SMS", "Push"] } },
        { type: "ProgramKit.ActionBar", id: "profile-actions", options: { actions: ["submit", "save", "fail"] } }
      ]
    },
    {
      type: "Category",
      id: "preferences",
      label: "Preferences",
      i18n: "steps.preferences",
      options: { presentation: { optional: "true" }, icon: { name: "settings", bundle: "lucide" } },
      elements: [{
        type: "Control",
        id: "plan",
        scope: "#/properties/plan",
        label: "Plan",
        i18n: "fields.plan",
        options: {
          component: "ProgramKit.SearchableSelect",
          componentVersion: "[1.0.0,2.0.0)",
          componentOptions: { dataSourceId: "catalog.plans", minimumCharacters: "1", debounceMilliseconds: "10", pageSize: "1", "filter.customerName": "/name" }
        }
      }]
    },
    {
      type: "Category",
      id: "confirm",
      label: "Confirm",
      i18n: "steps.confirm",
      rule: { effect: "SHOW", condition: { scope: "#/properties/name", schema: { const: "Ada" } } },
      options: { icon: { name: "check", bundle: "lucide" } },
      elements: [{ type: "Label", text: "Everything is ready.", i18n: "confirmation.ready" }]
    }
  ]
};

const messages = {
  en: {
    "steps.profile": "Profile",
    "steps.preferences": "Preferences",
    "steps.confirm": "Confirm",
    "fields.name": "Name",
    "fields.notes": "Notes",
    "fields.quantity": "Quantity",
    "fields.updates": "Product updates",
    "fields.role": "Role",
    "fields.channels": "Channels",
    "fields.plan": "Plan",
    "confirmation.ready": "Everything is ready.",
    "actions.submit": "Submit now",
    "actions.save": "Save draft",
    "actions.fail": "Test safe failure"
  },
  ar: {
    "steps.profile": "الملف الشخصي",
    "steps.preferences": "التفضيلات",
    "steps.confirm": "تأكيد",
    "fields.name": "الاسم",
    "fields.notes": "ملاحظات",
    "fields.quantity": "الكمية",
    "fields.updates": "تحديثات المنتج",
    "fields.role": "الدور",
    "fields.channels": "القنوات",
    "fields.plan": "الخطة",
    "confirmation.ready": "كل شيء جاهز.",
    "actions.submit": "إرسال الآن",
    "actions.save": "حفظ المسودة",
    "actions.fail": "اختبار فشل آمن"
  }
} as const;

const actionRequirements = [
  {
    actionId: "submit",
    handlerId: "fixture.submit",
    kind: "submit",
    label: { key: "actions.submit", defaultText: "Submit now" },
    requiresValidForm: true,
    icon: { name: "send", bundle: "lucide" }
  },
  {
    actionId: "save",
    handlerId: "fixture.save",
    kind: "saveDraft",
    label: { key: "actions.save", defaultText: "Save draft" },
    requiresValidForm: false
  },
  {
    actionId: "fail",
    handlerId: "fixture.fail",
    kind: "custom",
    label: { key: "actions.fail", defaultText: "Test safe failure" },
    requiresValidForm: false
  }
] as const satisfies readonly FormActionRequirement[];

const lookupRegistry = new FormLookupRegistry([{
  contract: {
    dataSourceId: "catalog.plans",
    contractVersion: "1.0.0",
    displayName: "Plans",
    execution: "server",
    supportsSearch: true,
    supportsPaging: true,
    filterKeys: ["customerName"],
    maximumPageSize: 1
  },
  search: async (query, context) => {
    await abortableDelay(20, context.signal);
    if (query.filters.customerName !== "Ada") throw new Error("dependent lookup filter missing");
    const arabic = context.locale === "ar";
    return query.cursor === undefined
      ? { items: [{ value: "professional", label: arabic ? "احترافي" : "Professional" }], nextCursor: "starter" }
      : { items: [{ value: "starter", label: arabic ? "مبتدئ" : "Starter" }] };
  },
  resolve: async (values, context) => values.map(value => ({
    value,
    label: value === "professional"
      ? context.locale === "ar" ? "احترافي" : "Professional"
      : context.locale === "ar" ? "مبتدئ" : "Starter"
  }))
}]);

function abortableDelay(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, milliseconds);
    signal.addEventListener("abort", () => { clearTimeout(timer); reject(new DOMException("Aborted", "AbortError")); }, { once: true });
  });
}

function validate(data: JsonValue): readonly RuntimeValidationIssue[] {
  if (generated(data)) return [];
  return (generated.errors ?? []).map(error => {
    const property = error.keyword === "required"
      ? error.params?.missingProperty
      : error.keyword === "additionalProperties"
        ? error.params?.additionalProperty
        : undefined;
    return {
      path: error.instancePath,
      keyword: error.keyword,
      message: error.message ?? error.keyword,
      ...(property === undefined ? {} : { property })
    };
  });
}

function CategoryLayout({ cells, enabled, path, renderers, schema: dataSchema, uischema, visible }: LayoutProps): ReactNode {
  if (!visible || !("elements" in uischema) || !Array.isArray(uischema.elements)) return null;
  return (
    <div className="fixture-category">
      {uischema.elements.map((element, index) => (
        <JsonFormsDispatch
          enabled={enabled}
          key={`${element.type}-${index}`}
          path={path}
          schema={dataSchema}
          uischema={element}
          {...(cells === undefined ? {} : { cells })}
          {...(renderers === undefined ? {} : { renderers })}
        />
      ))}
    </div>
  );
}

function TextLabel({ uischema, visible }: LayoutProps): ReactNode {
  if (!visible) return null;
  const text = "text" in uischema && typeof uischema.text === "string" ? uischema.text : "";
  return <p>{text}</p>;
}

const renderers = [
  programKitSearchableSelectRendererEntry,
  { tester: rankWith(10, uiTypeIs("Category")), renderer: withJsonFormsLayoutProps(CategoryLayout) },
  { tester: rankWith(10, uiTypeIs("Label")), renderer: withJsonFormsLayoutProps(TextLabel) }
];

function App(): ReactNode {
  const [locale, setLocale] = useState<keyof typeof messages>("en");
  const [data, setData] = useState<JsonValue>({});
  const [finished, setFinished] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [activeStep, setActiveStep] = useState("profile");
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
  }, [locale]);
  const runtime = useMemo(() => ({
    schema,
    uiSchema,
    validate,
    translate: (key: string, fallback: string) => messages[locale][key as keyof typeof messages.en] ?? fallback,
    actions: actionRequirements,
    dispatchAction: async (actionId: string, payload: JsonValue, context: { readonly signal: AbortSignal }) => {
      context.signal.throwIfAborted();
      await new Promise(resolve => setTimeout(resolve, 25));
      context.signal.throwIfAborted();
      if (actionId === "fail") throw new Error("private fixture detail must never reach the page");
      return { actionId, payload };
    }
  }), [locale]);
  const labels = locale === "ar"
    ? { navigation: "خطوات النموذج", progress: "اكتمال النموذج", back: "السابق", next: "التالي", skip: "تخطي", finish: "إنهاء" }
    : undefined;
  return (
    <main data-pk-theme="light">
      <header className="fixture-header">
        <div>
          <p className="fixture-eyebrow">Program Kit</p>
          <h1>Form journey acceptance</h1>
        </div>
        <button onClick={() => setLocale(value => value === "en" ? "ar" : "en")} type="button">
          {locale === "en" ? "العربية" : "English"}
        </button>
      </header>
      <p aria-live="polite" className="fixture-state">Active: {activeStep}</p>
      <ProgramKitJsonForms
        config={{
          programKitWizard: {
            labels,
            renderIcon: (icon: { name: string }) => <span data-icon={icon.name}>●</span>,
            onStepChange: (stepId: string) => setActiveStep(stepId),
            onFinish: () => setFinished(true)
          },
          programKitActions: {
            renderIcon: (icon: { name: string }) => <span data-action-icon={icon.name}>◆</span>,
            onResult: (action: { actionId: string }, result: { invoked: boolean; reason?: string }) => {
              setActionMessage(`${action.actionId}:${result.invoked ? "succeeded" : result.reason ?? "unknown"}`);
            }
          },
          programKitLookups: {
            registry: lookupRegistry,
            locale
          }
        }}
        data={data}
        onChange={next => setData(next)}
        renderers={renderers}
        runtime={runtime}
      />
      <p aria-live="polite" className="fixture-action-result">{actionMessage}</p>
      <p aria-live="polite" className="fixture-finished">{finished ? "Journey completed" : ""}</p>
      <output aria-hidden="true" className="fixture-form-data" hidden>{JSON.stringify(data)}</output>
    </main>
  );
}

const root = document.getElementById("root");
if (root === null) throw new Error("Fixture root is missing.");
createRoot(root).render(<App />);
