console.log("header.js file loaded");

document.addEventListener("DOMContentLoaded", function () {
  const menuItems = document.querySelectorAll(".menu-item");
  const submenus = document.querySelectorAll(".submenu");

  console.log("menuItems found:", menuItems.length);
  console.log("submenus found:", submenus.length);

  menuItems.forEach((item) => {
    console.log("Adding event listener to:", item);
    item.addEventListener("mouseenter", function () {
      const submenuId = item.getAttribute("data-submenu");
      console.log("Hovered on menu item:", submenuId);
      submenus.forEach((submenu) => {
        submenu.style.display = submenu.id === submenuId ? "flex" : "none";
        console.log("Showing submenu:", submenu.id);
      });
    });
  });

  const navbar = document.querySelector("#custom-navbar");
  if (navbar) {
    navbar.addEventListener("mouseleave", () => {
      console.log("Mouse left navbar");
      submenus.forEach((submenu) => {
        submenu.style.display = "none";
        console.log("Hiding submenu");
      });
    });
  } else {
    console.log("Navbar not found");
  }
});

