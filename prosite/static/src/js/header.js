console.log("header.js file loaded");

const intervalId = setInterval(() => {
    const items_with_menus = document.querySelectorAll(".item-with-submenu");
    const submenus = document.querySelectorAll(".submenu");
    const navbar = document.querySelector("#custom-navbar");

    console.log("check 2: " + items_with_menus.toString());
    console.log("check 3: " + submenus.toString());

    // Ensure both elements exist
    if (items_with_menus.length > 0 && submenus.length > 0 && navbar) {
        console.log("found submenus - check 4");

        // Stop the interval once elements are found
        clearInterval(intervalId);

        // Add event listeners to menu items
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

        // Add event listener to hide submenus on navbar mouseleave
        navbar.addEventListener("mouseleave", () => {
            console.log("removing submenus");
            submenus.forEach((submenu) => (submenu.style.display = "none"));
        });
    } else {
        console.log("Waiting for elements to load...");
    }
}, 500); // Check every 500ms
