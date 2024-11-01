/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _lt } from "@web/core/l10n/translation";

export class CodexDiagramField extends Component {
    setup() {
        this.action = useService("action");
    }
     startEditing() {
            const filename_value = this.props.record.data[this.props.filename];
            const mode = this.props.mode || 'atlas';
            if(!['atlas', 'min'].includes(mode)) {
                throw new Error(_lt('The mode optional value is atlas and min.'));
            }
            const action = {
                name: filename_value,
                type: 'ir.actions.client',
                tag: 'diagram_editor_action',
                target: 'fullscreen',
                resModel: this.props.record.resModel,
                resId: this.props.record.resId,
                fieldName: this.props.name,
                data: this.props.value|| undefined,
                title: filename_value,
                mode
            };
            this.action.doAction(action);
        }
        /**
         *
         * @override
        */
        get isSet() {
            return true;
        }

}

CodexDiagramField.template = "CodexDiagramField";
CodexDiagramField.props = {
    ...standardFieldProps,
    filename: { type: String, optional: true },
    mode: { type: String, optional: true },
};
CodexDiagramField.displayName = _lt("File");
CodexDiagramField.supportedTypes = ["text"];

CodexDiagramField.extractProps = ({ attrs }) => ({
    filename: attrs.filename,
    mode:attrs.mode,
});

registry.category("fields").add('diagram_editor', CodexDiagramField);
