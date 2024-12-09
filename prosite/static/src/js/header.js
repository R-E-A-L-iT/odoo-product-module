console.log("header.js file loaded");

const intervalId = setInterval(() => {
  const items_with_menus = document.querySelectorAll(".menu-item");
  const submenus = document.querySelectorAll(".submenu");
  const navbar = document.querySelector("#custom-navbar");

  console.log("check 2: " + items_with_menus.length.toString());
  console.log("check 3: " + submenus.length.toString());

  // Ensure all elements exist
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
          if (submenu.id === rel_submenu) {
            console.log("making submenu visible");
            submenu.classList.add("active");
            navbar.style.opacity = 1;
            navbar.classList.add("submenu-active"); // Add the class for black navbar
          } else {
            submenu.classList.remove("active");
            submenu.style.display = "none";
          }
        });
      });
    });

    // Add event listeners to keep submenus visible on hover
    submenus.forEach((submenu) => {
      submenu.addEventListener("mouseenter", function () {
        console.log("hovering over submenu");
        submenu.classList.add("active");
        navbar.style.opacity = 1;
        navbar.classList.add("submenu-active"); // Keep navbar fully black
      });

      submenu.addEventListener("mouseleave", function () {
        console.log("leaving submenu");
        submenu.classList.remove("active");
        navbar.style.opacity = 0;
        navbar.classList.remove("submenu-active"); // Reset navbar to partially transparent
      });
    });

    // Reset navbar and hide submenus when mouse leaves navbar entirely
    navbar.addEventListener("mouseleave", () => {
      console.log("removing submenus");
      submenus.forEach((submenu) => {
        submenu.classList.remove("active");
        navbar.style.opacity = 0;
      });
      navbar.classList.remove("submenu-active");
    });
  } else {
    console.log("Waiting for elements to load...");
  }
}, 500); // Check every 500ms
