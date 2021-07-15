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
        console.log(this.orderDetail);
        this.elems = this._getUpdatableElements();
        this._onLoad();
    },
    
    init: function (parent) {
        this._super(parent);
        //this._onLoad();
    },
    
    _onLoad: function () {
               
        this._updatePriceTotalsEvent();
    },
    
    _updatePriceTotalsEvent: function () {
        
        //Find All Products that Might Change the Price
        var vpList = document.querySelectorAll(".priceChange");
        for(var i = 0; i < vpList.length; i++){
            this._updatePriceTotals(vpList[i])
        }
        
    },
    
    _updatePriceTotals: function (target){
        var line_id = target.parentNode.parentNode.parentNode.querySelector("div").dataset["oeId"];
        console.log(target.parentNode.parentNode.parentNode.querySelector("div").dataset);

        
        
        this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/select/" + line_id,
            params: {access_token: this.orderDetail.token, 'selected': target.checked ? 'yes' : 'no'}})
    },
    
    _getUpdatableElements: function () {
        let $orderAmountUntaxed = $('[data-id="total_untaxed"]').find('span, b'),
            $orderAmountTotal = $('[data-id="total_amount"]').find('span, b'),
            $orderAmountUndiscounted = $('[data-id="amount_undiscounted"]').find('span, b');

        if (!$orderAmountUntaxed.length) {
            $orderAmountUntaxed = $orderAmountTotal.eq(1);
            $orderAmountTotal = $orderAmountTotal.eq(0).add($orderAmountTotal.eq(2));
        }

        return {
            $orderAmountUntaxed: $orderAmountUntaxed,
            $orderAmountTotal: $orderAmountTotal,
            $orderTotalsTable: $('#total'),
            $orderAmountUndiscounted: $orderAmountUndiscounted,
        };
    },
});
});
