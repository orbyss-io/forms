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
  UISchemaElement
} from "@jsonforms/core";
import type {
  JsonObject,
  JsonValue,
  ProgramKitTranslator,
  ProgramKitValidator,
  RuntimeValidationIssue
} from "@orbyss/program-kit-forms-contracts";
import {
  createPrecompiledJsonFormsAjvFacade,
  jsonFormsValidationErrorsToIssues,
  type JsonFormsCompatibleValidationError,
  type PrecompiledJsonFormsAjvFacade
} from "@orbyss/program-kit-forms-jsonforms-runtime";

export const programKitAngularFormsAdapterVersion = "1.0.0";

export interface ProgramKitJsonFormsAngularRuntime {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly validate: ProgramKitValidator;
  readonly translate: ProgramKitTranslator;
}

export interface ProgramKitJsonFormsAngularChange {
  readonly data: JsonValue;
  readonly issues: readonly RuntimeValidationIssue[];
}

interface JsonFormsAngularChangeEvent {
  readonly data: unknown;
  readonly errors?: readonly JsonFormsCompatibleValidationError[];
}

/**
 * Standalone Angular boundary over JSON Forms. The package is Angular-partial-compiled and shares
 * the same build-time validation and bounded-condition policy as React and Vue.
 */
@Component({
  selector: "program-kit-json-forms",
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
      (dataChange)="handleChange($event)"
    ></jsonforms>
  `
})
export class ProgramKitJsonFormsAngularComponent implements OnChanges {
  @Input({ required: true }) runtime!: ProgramKitJsonFormsAngularRuntime;
  @Input({ required: true }) data!: JsonValue;
  @Input() renderers: JsonFormsRendererRegistryEntry[] = [];
  @Input() readonly = false;
  @Input() config: Readonly<Record<string, unknown>> = Object.freeze({});
  @Output() readonly change = new EventEmitter<ProgramKitJsonFormsAngularChange>();

  ajv!: PrecompiledJsonFormsAjvFacade;
  uiSchema!: UISchemaElement;
  i18n!: { readonly translate: (key: string, fallback?: string) => string };

  ngOnChanges(changes: SimpleChanges): void {
    if (changes["runtime"] !== undefined) {
      this.ajv = createPrecompiledJsonFormsAjvFacade(this.runtime.schema, this.runtime.validate);
      this.uiSchema = this.runtime.uiSchema as unknown as UISchemaElement;
      this.i18n = Object.freeze({
        translate: (key: string, fallback?: string) => this.runtime.translate(key, fallback ?? "")
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
