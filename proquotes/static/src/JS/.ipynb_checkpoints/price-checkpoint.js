odoo.define('proquotes.price', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.price = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .priceChange': '_updatePriceTotalsEvent',
    },
    
    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
        this._onLoad();
    },
    
    _onLoad: function () {
        
        this._updatePriceTotalsEvent();
    },
    
    _updatePriceTotalsEvent: function () {
        
        //Find All Products that Might Change the Price
        let self = this;
        var vpList = document.querySelectorAll(".priceChange");
        var result = null;
        var line_ids = [];
        var targetsChecked = [];
        for(var i = 0; i < vpList.length; i++){
            targetsChecked.push(vpList[i].checked == true ? 'true' : 'false');
            line_ids.push(vpList[i].parentNode.parentNode.parentNode.querySelector("div").dataset["oeId"]);
            console.log(i);
        }
        this._updatePriceTotals(targetsChecked, line_ids);
    },
    
    _updatePriceTotals: function (targetsChecked, line_ids){
        let self = this;
        
        return this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/select",
            params: {access_token: this.orderDetail.token, line_ids: line_ids,'selected': targetsChecked}}).then((data) => {
            if (data) {
                self.$('#portalTotal').html($(data['sale_template']));
                this._updateView();
            }
        });
    },
    
    _multipleChoiceView: function () {
        var cbl = document.querySelectorAll(".multipleChoice");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var x = cb.parentNode.parentNode;
            var y = x.nextElementSibling;
            var k = 0;
            var firstChecked = null;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")){
                    break;
                } else {
                    var z = y.querySelector("input[type='radio']");
                    if(z.checked){
                        if(firstChecked == null){
                            firstChecked = ("multipleChoice" + i.toString() + "R" + k.toString());
                        }
                    }
                    z.className = "priceChange";
                    z.name = ("multipleChoice" + i.toString());
                    z.id = ("multipleChoice" + i.toString() + "R" + k.toString());
                    z.style.display="";
                    
                    
                    
                    var tdList = y.querySelectorAll("td");

                    for(var j = 0; j < tdList.length; j++){
                        var inner = tdList[j].innerHTML;
                        var l = document.createElement("label");
                        l.setAttribute("for", ("multipleChoice" + i.toString() + "R" + k.toString()));
                        l.style.width = "100%";
                        l.innerHTML = inner;
                        tdList[j].innerHTML = "";
                        tdList[j].append(l);
                    }
                }
            k++;
            y = y.nextElementSibling;
            }
            if(firstChecked != null){
                document.getElementById(firstChecked).checked = true;
            }
        }
    },
    
    _optionalView: function () {
        var cbl = document.querySelectorAll("input[type=checkbox].priceChange");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var row = cb.parentNode.parentNode;
            cb.name = ("optional" + i.toString());
            cb.id = ("optional" + i.toString() + "O");
            
            var tdList = row.querySelectorAll("td");

            for(var j = 0; j < tdList.length; j++){
                var inner = tdList[j].innerHTML;
                var l = document.createElement("label");
                l.setAttribute("for", ("optional" + i.toString() + "O"));
                l.style.width = "100%";
                l.innerHTML = inner;
                tdList[j].innerHTML = "";
                tdList[j].append(l);
            }
            
        }
    },
    
    _updateFoldDisplay: function () {
        var TRstyle;
        var cbl = document.querySelectorAll(".foldInput");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            if(cb.checked == true){
                TRstyle = "none";
            } else {
                TRstyle = "table-row";
            }
            var x = cb.parentNode.parentNode;
            var y = x.nextElementSibling;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")){
                    break;
                } else {
                    if(y.style != undefined && y.style != null){
                        y.style.display = TRstyle;
                    }
                }
            y = y.nextElementSibling;
            }
        }
        var subTotalList = document.getElementsByClassName("subtotal-destination");
        for(var i = 0; i < subTotalList.length; i++){
            var subTotal = subTotalList[i];
            subTotal.innerHTML = document.getElementsByClassName("subtotal-source")[i].innerHTML;
            
        }
    },
    
    _updateView: function () {
        this._multipleChoiceView();
        this._optionalView();
        this._updateFoldDisplay();
    },
});
});
