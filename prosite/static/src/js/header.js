console.log("header.js file loaded");

document.addEventListener("DOMContentLoaded", function () {
    const menuItems = document.querySelectorAll(".menu-item");
    const submenus = document.querySelectorAll(".submenu");

    menuItems.forEach((item) => {
        item.addEventListener("mouseenter", function () {
            console.log("mouseenter event listener added");
            const submenuId = item.getAttribute("data-submenu");
            submenus.forEach((submenu) => {
                submenu.style.display = submenu.id === submenuId ? "flex" : "none";
                console.log("mouseenter triggered");
            });
        });
    });

    document
        .querySelector("#custom-navbar")
        .addEventListener("mouseleave", () => {
            console.log("mouseleave event listener added");
            submenus.forEach((submenu) => {
                submenu.style.display = "none";
                console.log("mouseenter triggered");
            });
        });
    });
