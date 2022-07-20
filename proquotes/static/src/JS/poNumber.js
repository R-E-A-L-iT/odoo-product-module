odoo.define("proquotes.ponumber", function (require) {
	"use strict";
	var publicWidget = require("web.public.widget");

	publicWidget.registry.ponumber = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		events: {
			"change .poNumber": "_update_po_number",
			"change #poFile": "_update_po_file",
		},

		async start() {
			await this._super(...arguments);
			this.orderDetail = this.$el.find("table#sales_order_table").data();
		},

		_update_po_number: function (ev) {
			var target = ev.currentTarget;
			var poNumber = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/ponumber",
				params: {
					access_token: this.orderDetail.token,
					ponumber: poNumber,
				},
			});
		},

		_update_po_file: function (ev) {
			var target = ev.currentTarget;
			var poFile = target.files;
			console.log(poFile);
			var reader = new FileReader();
			console.log(this.orderDetail.orderId);
			reader.readAsBinaryString(poFile[0]);
			reader.onloadend = (function (id, token) {
				return this._rpc({
					route: "/my/orders/" + id + "/poFile",
					params: {
						access_token: token,
						poFile: reader.result,
					},
				});
			})(this.orderDetail.orderId, this.prderDetail.token);
		},
	});
});
