console.log("header.js file loaded");

const intervalId = setInterval(() => {
    const items_with_menus = document.querySelectorAll(".item-with-submenu")
    const submenus = document.querySelectorAll(".submenu")

    console.log("check 2");

    if (items_with_menus.length > 0 && submenus.length > 0) {
      console.log("found submenus - check 3");

      // make submenus visible on hover
      items_with_menus.forEach((item) => {
        item.addEventListener("mouseenter", function () {
          const rel_submenu = item.getAttribute("data-submenu");
          console.log("found related submenu");
          submenus.forEach((submenu) => {
            console.log("making submenu visible");
            submenu.style.display =
              submenu.id === rel_submenu ? "flex" : "none";
          });
        });
      });

      // make all submenus invisible on leave header
      navbar.addEventListener("mouseleave", () => {
        console.log("removing submenus");
        submenus.forEach((submenu) => (submenu.style.display = "none"));
      });
    } else {
      console.log("Waiting for elements to load...");
    }
}, 500); // Check every 500ms
