/**
 * Comportamiento de la home, reescrito sin jQuery ni css-vars-ponyfill.
 *
 * Antes este archivo dependia de jQuery (88 KB) y el layout cargaba ademas
 * css-vars-ponyfill (23 KB) para emular variables CSS en navegadores que
 * ninguna version de IE llego a usar. Entre los dos sumaban ~123 KB de JS
 * para una pagina que hace scroll y resalta el item activo del menu: se
 * reescribio con la API del navegador (querySelector, classList,
 * addEventListener, IntersectionObserver no hace falta — alcanza con scroll).
 *
 * Se mantiene ES5 (var, function) a proposito: el sitio no tiene build step
 * de JS, asi que lo que se escribe es lo que se sirve.
 *
 * El scroll suave lo hace `scroll-behavior: smooth` en el CSS
 * (content.scss), que hoy soportan todos los motores. Por eso ya no hay
 * fallback de animacion en JS: era codigo muerto.
 */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  ready(function () {
    var siteHead = document.getElementById("site-head");
    var fixedNav = document.querySelector(".fixed-nav");
    var posts = document.querySelectorAll(".post");
    var postHolders = document.querySelectorAll(".post-holder");
    var lastPost = document.querySelector(".post.last");

    // El separador decorativo despues de la ultima seccion no se muestra.
    if (lastPost && lastPost.nextElementSibling &&
        lastPost.nextElementSibling.classList.contains("post-after")) {
      lastPost.nextElementSibling.style.display = "none";
    }

    if (siteHead && fixedNav) {
      var ticking = false;

      var onScroll = function () {
        var w = window.pageYOffset || document.documentElement.scrollTop;
        var top = siteHead.offsetTop;
        var bottom = top + siteHead.offsetHeight - 100;

        // Dentro del header la nav fija se esconde; fuera, se muestra.
        if (w >= Math.floor(top) && w <= Math.ceil(bottom)) {
          fixedNav.style.display = "none";
        } else {
          fixedNav.style.display = "flex";
        }

        var doc = document.documentElement;
        var footer = document.querySelector(".site-footer");
        var nearBottom = (window.innerHeight + w) >
          (doc.scrollHeight - (footer ? footer.offsetHeight : 0));

        if (nearBottom) {
          // Al llegar al pie, se marca el ultimo item del menu.
          setActive(postHolders.length);
        } else {
          for (var i = 0; i < posts.length; i++) {
            var post = posts[i];
            var f = post.offsetTop;
            var b = f + post.offsetHeight;
            var holder = post.parentElement;
            /* item_index es 1-based: el template numera los items del menu
               con (add $index_val 1) y el primer hijo de <main> es
               .fixed-nav, asi que el post-holder n-esimo queda en la
               posicion n dentro de su padre. jQuery resolvia esto con
               .index(); con JS puro hay que sumar 1 a mano, porque
               indexOf devuelve 0-based y el item 0 no existe. */
            var idx = Array.prototype.indexOf.call(
              holder.parentElement.children, holder
            );
            var after = holder.previousElementSibling;

            post.setAttribute("item_index", idx);

            if (w >= f && w <= b) {
              setActive(idx);
              if (after && after.classList.contains("post-after")) {
                after.style.display = "none";
              }
            } else if (after && after.classList.contains("post-after")) {
              after.style.display = "";
            }
          }
        }
        ticking = false;
      };

      window.addEventListener("scroll", function () {
        if (!ticking) {
          window.requestAnimationFrame(onScroll);
          ticking = true;
        }
      }, { passive: true });

      onScroll();
    }

    function setActive(idx) {
      var items = document.querySelectorAll(".fn-item");
      for (var i = 0; i < items.length; i++) {
        items[i].classList.remove("active");
      }
      var target = document.querySelector('.fn-item[item_index="' + idx + '"]');
      if (target) {
        target.classList.add("active");
      }
    }

    // Icono de vineta en las listas, tomado de la variable CSS de marca.
    // Antes esto lo hacia css-vars-ponyfill; getComputedStyle lee la custom
    // property nativamente, sin polyfill.
    var ulLiIcon = getComputedStyle(document.documentElement)
      .getPropertyValue("--ul-li-icon");
    if (ulLiIcon && ulLiIcon.trim().length > 0) {
      ulLiIcon = ulLiIcon.trim();
      var lists = document.querySelectorAll("ul");
      for (var i = 0; i < lists.length; i++) {
        lists[i].classList.add("fa-ul");
        var lis = lists[i].children;
        for (var j = 0; j < lis.length; j++) {
          if (lis[j].tagName !== "LI") { continue; }
          var span = document.createElement("span");
          span.className = "fa-li";
          var icon = document.createElement("i");
          icon.className = "fa " + ulLiIcon;
          span.appendChild(icon);
          lis[j].insertBefore(span, lis[j].firstChild);
        }
      }
    }

    // Las comillas decorativas de los blockquotes ya no se inyectan acá: eran
    // dos iconos de ForkAwesome dentro del párrafo, y el de cierre no entraba
    // en la última línea, así que caía solo en un renglón abajo. Ahora son un
    // ::before tipográfico colgado en el margen (ver content.scss), que no
    // participa del flujo del texto y no depende de la tipografía de iconos.

    // Sintaxis @icono@ en el contenido -> <i class="fa icono">.
    // `icons` viene de icons.js. Si no esta definido, no se hace nada.
    if (typeof icons === "undefined" || !icons.length) { return; }

    for (var p = 0; p < posts.length; p++) {
      var html = posts[p].innerHTML;
      var changed = false;
      for (var n = 0; n < icons.length; n++) {
        var token = "@" + icons[n] + "@";
        if (html.indexOf(token) === -1) { continue; }
        html = html.split(token)
          .join('<i class="fa ' + icons[n] + '"></i>');
        changed = true;
      }
      if (changed) {
        posts[p].innerHTML = html;
      }
    }
  });
})();
