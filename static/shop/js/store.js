document.addEventListener("DOMContentLoaded", function(){

  function pad(n){
    return String(n).padStart(2,"0");
  }

  function updateCountdown(){
    const cards = document.querySelectorAll(".bk-so-card");

    cards.forEach(card => {
      const endStr = card.dataset.end;
      if(!endStr) return;

      const badge = card.querySelector(".bk-so-countdown");
      if(!badge) return;

      const end = new Date(endStr.replace(" ", "T")).getTime();
      const now = new Date().getTime();
      const diff = end - now;

      if(diff <= 0){
        badge.textContent = "انتهى";
        badge.classList.remove("text-bg-dark");
        badge.classList.add("text-bg-danger");
        return;
      }

      const h = Math.floor(diff / (1000*60*60));
      const m = Math.floor((diff % (1000*60*60)) / (1000*60));
      const s = Math.floor((diff % (1000*60)) / 1000);

      badge.textContent = `${pad(h)}:${pad(m)}:${pad(s)}`;
    });
  }

  updateCountdown();
  setInterval(updateCountdown, 1000);

});