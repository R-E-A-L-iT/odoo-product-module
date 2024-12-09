document.addEventListener("DOMContentLoaded", function () {
  const menuItems = document.querySelectorAll(".menu-item");
  const submenus = document.querySelectorAll(".submenu");

  menuItems.forEach((item) => {
    item.addEventListener("mouseenter", function () {
      const submenuId = item.getAttribute("data-submenu");
      submenus.forEach((submenu) => {
        submenu.style.display = submenu.id === submenuId ? "flex" : "none";
      });
    });
  });

  document
    .querySelector("#custom-navbar")
    .addEventListener("mouseleave", () => {
      submenus.forEach((submenu) => (submenu.style.display = "none"));
    });
});
