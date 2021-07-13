odoo.define('proquotes.multipleChoice', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.multipleChoice = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
    },
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        var TRstyle;
        var cbl = document.querySelectorAll(".multipleChoice");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var x = cb.parentNode.parentNode;
            var y = x.nextElementSibling;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")){
                    break;
                } else {
                    var childTD = [];
                    for(var j = 0; j < y.childNodes.length; j++){
                        childTD[j] = y.childNodes.shift();
                    }
                    var z = document.createElement("input");
                    z.type = "radio";
                    z.name = ("multipleChoice" + i);
                    
                    var l = document.createElement("label")
                    l.for = ("multipleChoice" + i);
                    
                    l.childNodes = childTD;
                    l.childNodes[1].prepend(z);

                    
                }
            y = y.nextElementSibling;
            }
        }
    },
});
});
