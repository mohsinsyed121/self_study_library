// Shared behaviour for all pages.
document.addEventListener("DOMContentLoaded", function () {
  // 1) Confirmation prompts: <form data-confirm="Are you sure?"> or <a data-confirm="...">
  document.querySelectorAll("[data-confirm]").forEach(function (element) {
    var eventName = element.tagName === "FORM" ? "submit" : "click";
    element.addEventListener(eventName, function (event) {
      if (!window.confirm(element.getAttribute("data-confirm"))) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    });
  });

  // 2) Print button: <button data-print>Print</button>
  document.querySelectorAll("[data-print]").forEach(function (btn) {
    btn.addEventListener("click", function () { window.print(); });
  });
});
