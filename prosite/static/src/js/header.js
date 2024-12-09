console.log("header.js file loaded");

odoo.define("prosite.header", function (require) {
  "use strict";

  $(document).ready(function () {
    console.log("header.js loaded using jQuery");

    const menuItems = $(".menu-item");
    const submenus = $(".submenu");

    console.log("menuItems found:", menuItems.length);
    console.log("submenus found:", submenus.length);

    menuItems.on("mouseenter", function () {
      const submenuId = $(this).data("submenu");
      console.log("Hovered on menu item:", submenuId);

      submenus.each(function () {
        const submenu = $(this);
        submenu.css(
          "display",
          submenu.attr("id") === submenuId ? "flex" : "none"
        );
      });
    });

    $("#custom-navbar").on("mouseleave", function () {
      submenus.css("display", "none");
    });
  });
});
