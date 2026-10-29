      // 시각은 scripts/chart_motion.py 의 motion_end() 와 같아야 한다
      const cards = document.querySelectorAll("#slide .card");
      SLIDE.items.forEach((it, i) => {
        const t0 = 0.3 + i * 0.2;
        tl.fromTo(cards[i], { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, t0);
        countUp(cards[i].querySelector(".cv"), it, t0 + 0.2, 1.2);
      });
      if (SLIDE.hi >= 0) {
        // 강조 칸만 남기고 나머지 칸은 한 톤 낮춘다 (.card 는 등장, .ci 는 흐림을 맡아 서로 덮어쓰지 않게)
        tl.fromTo("#slide .card:not(.hi) .ci", { opacity: 1 }, { opacity: 0.5, duration: 0.5, ease: "power2.out" }, 2.2);
        tl.fromTo("#slide .card.hi .cv", { scale: 1 }, { scale: 1.08, duration: 0.25, ease: "power2.out", transformOrigin: "left center" }, 2.8);
        tl.to("#slide .card.hi .cv", { scale: 1, duration: 0.35, ease: "power2.inOut" }, 3.05);
      }
