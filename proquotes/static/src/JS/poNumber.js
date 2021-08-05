odoo.define('proquotes.ponumber', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.price = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .poNumber': '_update_po_number',
    },
    
    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
    },
    
    _update_po_number: function(ev){
        var target = ev.currentTarget;
        var poNumber = target.value;
        return this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/ponumber",
            params: {access_token: this.orderDetail.token, ponumber: poNumber}})        
    },
    
});
});
