import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
  type OnChanges,
  type SimpleChanges
} from "@angular/core";
import { JsonFormsModule } from "@jsonforms/angular";
import type {
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
  ValidationMode
} from "@jsonforms/core";
import type {
  JsonObject,
  JsonValue,
  OrbyssTranslator,
  OrbyssValidator,
  RuntimeValidationIssue
} from "@orbyss-io/forms-contracts";
import {
  createJsonFormsTranslatorAdapter,
  createPrecompiledJsonFormsAjvFacade,
  jsonFormsValidationErrorsToIssues,
  type JsonFormsTranslatorAdapter,
  type JsonFormsCompatibleValidationError,
  type PrecompiledJsonFormsAjvFacade
} from "@orbyss-io/forms-jsonforms-runtime";

export const programKitAngularFormsAdapterVersion = "1.0.0";

export interface OrbyssJsonFormsAngularRuntime {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly validate: OrbyssValidator;
  readonly translate: OrbyssTranslator;
}

export interface OrbyssJsonFormsAngularChange {
  readonly data: JsonValue;
  readonly issues: readonly RuntimeValidationIssue[];
}

interface JsonFormsAngularChangeEvent {
  readonly data: unknown;
  readonly errors?: readonly JsonFormsCompatibleValidationError[];
}

/**
 * Thin standalone Angular boundary over JSON Forms. The package owns validation integration only;
 * renderer components and styling are supplied by the consuming application.
 */
@Component({
  selector: "orbyss-forms-json-forms",
  standalone: true,
  imports: [JsonFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <jsonforms
      [ajv]="$any(ajv)"
      [config]="config"
      [data]="data"
      [i18n]="i18n"
      [readonly]="readonly"
      [renderers]="renderers"
      [schema]="runtime.schema"
      [uischema]="uiSchema"
      [validationMode]="validationMode"
      (dataChange)="handleChange($event)"
    ></jsonforms>
  `
})
export class OrbyssJsonFormsAngularComponent implements OnChanges {
  @Input({ required: true }) runtime!: OrbyssJsonFormsAngularRuntime;
  @Input({ required: true }) data!: JsonValue;
  @Input({ required: true }) renderers!: JsonFormsRendererRegistryEntry[];
  @Input() readonly = false;
  @Input() config: Readonly<Record<string, unknown>> = Object.freeze({});
  @Input() validationMode: ValidationMode = "ValidateAndHide";
  @Output() readonly change = new EventEmitter<OrbyssJsonFormsAngularChange>();

  ajv!: PrecompiledJsonFormsAjvFacade;
  uiSchema!: UISchemaElement;
  i18n!: { readonly translate: JsonFormsTranslatorAdapter };

  ngOnChanges(changes: SimpleChanges): void {
    if (this.renderers.length === 0) {
      throw new Error("Orbyss Forms's Angular binding requires consumer-supplied JSON Forms renderers.");
    }
    if (changes["runtime"] !== undefined) {
      this.ajv = createPrecompiledJsonFormsAjvFacade(this.runtime.schema, this.runtime.validate);
      this.uiSchema = this.runtime.uiSchema as unknown as UISchemaElement;
      this.i18n = Object.freeze({
        translate: createJsonFormsTranslatorAdapter(this.runtime.translate)
      });
    }
  }

  handleChange(event: JsonFormsAngularChangeEvent): void {
    this.change.emit(Object.freeze({
      data: event.data as JsonValue,
      issues: jsonFormsValidationErrorsToIssues(event.errors ?? [])
    }));
  }
}
