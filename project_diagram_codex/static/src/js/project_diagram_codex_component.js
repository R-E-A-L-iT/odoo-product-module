odoo.define('project_diagram_codex.CodexDiagram', function (require) {
    'use strict';
    const { Component } = owl;
    const { onMounted, useRef } = owl;
    const core = require('web.core');

    class CodexDiagram extends Component {
        constructor(parent, props) {
            super(...arguments);
            this.frameRef = useRef('CodexDiagram');
            this.handleMessageEvent = this._handleMessageEvent.bind(this);
            onMounted(() => {
                this.frame = this.frameRef.el;
                this.startEditing();
            });
        }

        get url() {
            var url = this.props.drawDomain + '?proto=json&spin=1';

            if (this.props.mode != null) {
                url += '&ui=' + this.props.mode;
            }

            if (this.props.libraries != null) {
                url += '&libraries=1';
            }

            if (this.props.config != null) {
                url += '&configure=1';
            }

            if (this.props.urlParams != null) {
                url += '&' + this.props.urlParams.join('&');
            }
            return url;
        }
        postMessage (msg) {
            if (this.frame != null) {
                this.frame.contentWindow.postMessage(JSON.stringify(msg), '*');
            }
        }
        initializeEditor () {
            this.postMessage({
                action: 'load',
                saveAndExit: '1',
                modified: 'unsavedChanges',
                xml: this.props.data,
                title: this.props.title
            });
        }

        configureEditor () {
            this.postMessage({
                action: 'configure',
                config: this.props.config
            });
        }

        setStatus(messageKey, modified) {
            this.postMessage({
                action: 'status',
                messageKey: messageKey,
                modified: modified
            });
        }

        startEditing() {
            window.addEventListener('message', this.handleMessageEvent);
        }

        _handleMessageEvent(evt) {
            if (this.frame != null && evt.source == this.frame.contentWindow &&
                evt.data.length > 0) {
                try {
                    var msg = JSON.parse(evt.data);

                    if (msg != null) {
                        this.handleMessage(msg);
                    }
                } catch (e) {
                    console.error(e);
                }
            }
        }

        handleMessage(msg) {
            switch (msg.event) {
                case 'configure':
                    this.configureEditor();
                    break;
                case 'init':
                    this.initializeEditor();
                    break;
                case 'save':
                    this.saveDiagram(msg.xml, msg.exit);
                    break;
                case 'exit':
                    this.exitDiagram();
                    break;
                default:
                    console.log(msg.event);
                    break;
            }
        }

        exitDiagram() {
            core.bus.trigger('diagram_exit', {});
        }

        saveDiagram(xml, exit) {
            core.bus.trigger('diagram_save', { xml, exit });
        }

        done(exit) {
            if(exit) {
                this.exitDiagram();
            } else {
                this.setStatus('allChangesSaved', false);
            }
        }
    }

    Object.assign(CodexDiagram, {
        template: 'CodexDiagram',
        defaultProps: {
            xml: null,
            format: 'xml',
            libraries: true,
            config: null,
            urlParams: null,
            drawDomain: 'https://embed.diagrams.net/',
        }
    });

    return CodexDiagram;
});