import options from "web_editor.snippets.options";

options.registry.HeaderSnippetOptions = options.Class.extend({
  toggleSubnav(previewMode, widgetValue) {
    this.$target.toggleClass("has-subnav", widgetValue === "true");
  },
});
