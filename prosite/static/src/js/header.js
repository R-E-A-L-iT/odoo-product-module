console.log("header.js file loaded");

window.addEventListener("load", function () {
  console.log("header.js loaded after window load");

  const menuItems = document.querySelectorAll(".menu-item");
  const submenus = document.querySelectorAll(".submenu");

  console.log("menuItems found:", menuItems.length);
  console.log("submenus found:", submenus.length);

  menuItems.forEach((item) => {
    item.addEventListener("mouseenter", function () {
      const submenuId = item.getAttribute("data-submenu");
      console.log("Hovered on menu item:", submenuId);
      submenus.forEach((submenu) => {
        submenu.style.display = submenu.id === submenuId ? "flex" : "none";
      });
    });
  });

  const navbar = document.querySelector("#custom-navbar");
  if (navbar) {
    navbar.addEventListener("mouseleave", () => {
      submenus.forEach((submenu) => (submenu.style.display = "none"));
    });
  } else {
    console.log("Navbar not found");
  }
});
