// Seat map: filter seats by status using the buttons above the map.
document.addEventListener("DOMContentLoaded", function () {
  var buttons = document.querySelectorAll("[data-seat-filter]");
  var seats = document.querySelectorAll("[data-seat-status]");
  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      var wanted = button.getAttribute("data-seat-filter");
      buttons.forEach(function (b) { b.classList.remove("active"); });
      button.classList.add("active");
      seats.forEach(function (seat) {
        var show = wanted === "all" || seat.getAttribute("data-seat-status") === wanted;
        seat.parentElement.classList.toggle("d-none", !show);
      });
    });
  });
});
