odoo.define('project_diagram_codex.diagram_editor_action', function (require) {
    'use strict';
    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const { ComponentWrapper } = require('web.OwlCompatibility');
    const CodexDiagram = require('project_diagram_codex.CodexDiagram');

    const CodexDiagramAction = AbstractAction.extend({
        hasControlPanel: true,
        init(parent, action, options={}) {
            this._super(...arguments);
            this.CodexDiagramWrapper = undefined;
            this.action = action;
            this.props = {
                mode: action.mode,
                data: action.data,
                title: action.title
            };

            core.bus.on('diagram_save', this, async (ev) => {
                await this._rpc({
                    model: this.action.resModel,
                    method: 'write',
                    args: [
                        [this.action.resId],
                        {[this.action.fieldName]: ev.xml}
                    ]
                });
                this.CodexDiagramWrapper.componentRef.comp.done(ev.exit);
            });
            core.bus.on('diagram_exit', this, ev => {
                this.trigger_up('breadcrumb_clicked', {
                    controllerID: this.controlPanelProps.breadcrumbs.at(-1).controllerID
                });
            });
        },
        async start() {
            await this._super(...arguments);
            this.$el.find('.o_cp_bottom').hide();
            this.CodexDiagramWrapper = new ComponentWrapper(this, CodexDiagram, this.props);
            return this.CodexDiagramWrapper.mount(this.el.querySelector('.o_content'));
        }
    });

    core.action_registry.add('diagram_editor_action', CodexDiagramAction);
    return CodexDiagramAction;
});