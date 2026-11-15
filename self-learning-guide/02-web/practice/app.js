// Runs in the browser. Recalculate money in whenever the number changes.
const price = Number(document.getElementById("price").textContent);
const cupsBox = document.getElementById("cups");
const moneyIn = document.getElementById("money-in");

cupsBox.addEventListener("input", () => {
  const cups = Number(cupsBox.value);
  moneyIn.textContent = cups * price;
});
