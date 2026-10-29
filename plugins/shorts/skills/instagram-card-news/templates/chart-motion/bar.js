      // 시각은 scripts/chart_motion.py 의 motion_end() 와 같아야 한다
      const rows = document.querySelectorAll("#slide .row");
      SLIDE.items.forEach((it, i) => {
        const bar = rows[i].querySelector(".bar");
        const val = rows[i].querySelector(".val");
        const t0 = 0.35 + i * 0.12;
        tl.fromTo(bar, { width: 0 }, { width: it.w, duration: 1.4, ease: "power3.out" }, t0);
        tl.fromTo(val, { x: 0 }, { x: it.w, duration: 1.4, ease: "power3.out" }, t0);
        tl.fromTo(val, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power1.out" }, t0);
        countUp(val, it, t0, 1.4);
        const clip = rows[i].querySelector(".barclip");
        if (clip) tl.set(clip, { width: it.w }, 0);
      });
      if (SLIDE.hi >= 0) {
        // 1위만 남기고 나머지는 한 톤 낮춘 뒤, 1위 막대에 빛이 한 번 지나간다
        tl.fromTo("#slide .row:not(.hi)", { opacity: 1 }, { opacity: 0.45, duration: 0.5, ease: "power2.out" }, 2.5);
        tl.fromTo("#slide .row.hi .shine", { x: 0 }, { x: 900, duration: 0.8, ease: "power2.inOut" }, 2.9);
        tl.fromTo("#slide .row.hi .val", { scale: 1 }, { scale: 1.12, duration: 0.25, ease: "power2.out", transformOrigin: "left center" }, 3.0);
        tl.to("#slide .row.hi .val", { scale: 1, duration: 0.35, ease: "power2.inOut" }, 3.25);
      }
