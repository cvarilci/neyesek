(function () {
  "use strict";

  var SELECTED_KEY = "neyesek:selected";
  var SHOPPING_KEY = "neyesek:shopping";

  // ---- localStorage yardımcıları ----------------------------------------

  function readJSON(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      if (!raw) return fallback;
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : fallback;
    } catch (err) {
      return fallback;
    }
  }

  function writeJSON(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
      // localStorage kullanılamıyorsa (gizli sekme vb.) sessizce yoksay.
    }
  }

  function getSelected() {
    return readJSON(SELECTED_KEY, []);
  }

  function setSelected(items) {
    writeJSON(SELECTED_KEY, items);
  }

  function getShopping() {
    return readJSON(SHOPPING_KEY, []);
  }

  function setShopping(items) {
    writeJSON(SHOPPING_KEY, items);
  }

  // ---- Ortak: üst bardaki alışveriş listesi rozeti -----------------------

  function updateShoppingBadge() {
    var badge = document.getElementById("shopping-count");
    if (!badge) return;
    var items = getShopping();
    var remaining = items.filter(function (item) {
      return !item.checked;
    }).length;
    if (remaining > 0) {
      badge.textContent = String(remaining);
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  }

  // ---- Ana sayfa: malzeme seçimi ------------------------------------------

  function initHomePage() {
    var searchInput = document.getElementById("ingredient-search");
    var chipList = document.getElementById("selected-chips");
    var showRecipesBtn = document.getElementById("show-recipes");
    if (!searchInput || !chipList || !showRecipesBtn) return;

    var searchResults = document.getElementById("search-results");
    var searchStatus = document.getElementById("search-status");
    var emptyHint = document.getElementById("empty-selection-hint");
    var debounceTimer = null;
    var activeIndex = -1;
    var currentResults = [];

    function renderChips() {
      var items = getSelected();
      chipList.textContent = "";
      items.forEach(function (item) {
        var chip = document.createElement("span");
        chip.className = "chip";

        var label = document.createElement("span");
        label.textContent = item.name;
        chip.appendChild(label);

        var removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "chip__remove";
        removeBtn.setAttribute("aria-label", item.name + " malzemesini kaldır");
        removeBtn.textContent = "×";
        removeBtn.addEventListener("click", function () {
          removeIngredient(item.slug);
        });
        chip.appendChild(removeBtn);

        chipList.appendChild(chip);
      });

      document.querySelectorAll(".chip-option").forEach(function (btn) {
        var isSelected = items.some(function (item) {
          return item.slug === btn.dataset.slug;
        });
        btn.classList.toggle("chip-option--selected", isSelected);
      });
    }

    function addIngredient(slug, name) {
      var items = getSelected();
      if (items.some(function (item) { return item.slug === slug; })) return;
      items.push({ slug: slug, name: name });
      setSelected(items);
      renderChips();
    }

    function removeIngredient(slug) {
      var items = getSelected().filter(function (item) {
        return item.slug !== slug;
      });
      setSelected(items);
      renderChips();
    }

    // ---- Otomatik tamamlama ----

    function closeResults() {
      searchResults.hidden = true;
      searchResults.textContent = "";
      currentResults = [];
      activeIndex = -1;
    }

    function renderResults(results) {
      currentResults = results;
      activeIndex = -1;
      searchResults.textContent = "";

      if (results.length === 0) {
        searchResults.hidden = true;
        if (searchStatus) searchStatus.textContent = "Sonuç bulunamadı.";
        return;
      }

      if (searchStatus) {
        searchStatus.textContent = results.length + " sonuç bulundu.";
      }

      results.forEach(function (ingredient, index) {
        var li = document.createElement("li");
        li.setAttribute("role", "option");
        li.className = "search-result";
        li.textContent = ingredient.name;
        li.addEventListener("mousedown", function (event) {
          // blur olayından önce çalışsın diye mousedown kullanıldı.
          event.preventDefault();
          addIngredient(ingredient.slug, ingredient.name);
          searchInput.value = "";
          closeResults();
        });
        li.addEventListener("mouseenter", function () {
          setActiveIndex(index);
        });
        searchResults.appendChild(li);
      });

      searchResults.hidden = false;
    }

    function setActiveIndex(index) {
      var options = searchResults.querySelectorAll(".search-result");
      options.forEach(function (opt) {
        opt.classList.remove("search-result--active");
      });
      if (index >= 0 && index < options.length) {
        options[index].classList.add("search-result--active");
        activeIndex = index;
      } else {
        activeIndex = -1;
      }
    }

    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim();
      window.clearTimeout(debounceTimer);
      if (!query) {
        closeResults();
        if (searchStatus) searchStatus.textContent = "";
        return;
      }
      if (searchStatus) searchStatus.textContent = "Aranıyor...";
      debounceTimer = window.setTimeout(function () {
        fetch("/api/malzemeler/?q=" + encodeURIComponent(query))
          .then(function (response) {
            return response.ok ? response.json() : { results: [] };
          })
          .then(function (data) {
            renderResults(data.results || []);
          })
          .catch(function () {
            closeResults();
            if (searchStatus) searchStatus.textContent = "Arama sırasında bir sorun oluştu.";
          });
      }, 250);
    });

    searchInput.addEventListener("keydown", function (event) {
      if (searchResults.hidden || currentResults.length === 0) return;

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex(Math.min(activeIndex + 1, currentResults.length - 1));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex(Math.max(activeIndex - 1, 0));
      } else if (event.key === "Enter") {
        if (activeIndex >= 0) {
          event.preventDefault();
          var ingredient = currentResults[activeIndex];
          addIngredient(ingredient.slug, ingredient.name);
          searchInput.value = "";
          closeResults();
        }
      } else if (event.key === "Escape") {
        closeResults();
      }
    });

    searchInput.addEventListener("blur", function () {
      window.setTimeout(closeResults, 100);
    });

    // ---- Popüler malzeme butonları ----

    document.querySelectorAll(".chip-option").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var items = getSelected();
        var already = items.some(function (item) { return item.slug === btn.dataset.slug; });
        if (already) {
          removeIngredient(btn.dataset.slug);
        } else {
          addIngredient(btn.dataset.slug, btn.dataset.name);
        }
      });
    });

    // ---- Süre / kategori filtreleri (tek seçim, sayfa içi durum) ----

    function initSingleSelect(containerId) {
      var container = document.getElementById(containerId);
      if (!container) return { getValue: function () { return ""; } };
      var selectedValue = "";
      container.querySelectorAll(".filter-option").forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (selectedValue === btn.dataset.value) {
            selectedValue = "";
            btn.classList.remove("filter-option--selected");
            return;
          }
          selectedValue = btn.dataset.value;
          container.querySelectorAll(".filter-option").forEach(function (b) {
            b.classList.remove("filter-option--selected");
          });
          btn.classList.add("filter-option--selected");
        });
      });
      return {
        getValue: function () {
          return selectedValue;
        },
      };
    }

    var durationFilter = initSingleSelect("duration-options");
    var categoryFilter = initSingleSelect("category-options");

    // ---- Tarifleri göster ----

    showRecipesBtn.addEventListener("click", function () {
      var items = getSelected();
      if (items.length === 0) {
        if (emptyHint) emptyHint.hidden = false;
        return;
      }
      if (emptyHint) emptyHint.hidden = true;

      var slugs = items.map(function (item) { return item.slug; }).join(",");
      var params = new URLSearchParams();
      params.set("m", slugs);
      var sure = durationFilter.getValue();
      if (sure) params.set("sure", sure);
      var kategori = categoryFilter.getValue();
      if (kategori) params.set("kategori", kategori);

      window.location.href = "/tarifler/?" + params.toString();
    });

    renderChips();
  }

  // ---- Tarif detayı: eksikleri listeye ekle -------------------------------

  function initDetailPage() {
    var addBtn = document.getElementById("add-missing-to-list");
    var dataScript = document.getElementById("missing-ingredients-data");
    if (!addBtn || !dataScript) return;

    var missingItems = [];
    try {
      missingItems = JSON.parse(dataScript.textContent) || [];
    } catch (err) {
      missingItems = [];
    }

    addBtn.addEventListener("click", function () {
      var shopping = getShopping();
      var existingSlugs = shopping.map(function (item) { return item.slug; });

      missingItems.forEach(function (item) {
        if (existingSlugs.indexOf(item.slug) === -1) {
          shopping.push({ slug: item.slug, name: item.name, checked: false });
          existingSlugs.push(item.slug);
        }
      });

      setShopping(shopping);
      updateShoppingBadge();
      addBtn.textContent = "Listeye eklendi ✓";
      addBtn.disabled = true;
    });
  }

  // ---- Alışveriş listesi sayfası ------------------------------------------

  function initShoppingListPage() {
    var list = document.getElementById("shopping-list-items");
    if (!list) return;

    var emptyMessage = document.getElementById("shopping-list-empty");
    var copyBtn = document.getElementById("copy-list");
    var clearBtn = document.getElementById("clear-list");

    function render() {
      var items = getShopping();
      list.textContent = "";

      if (items.length === 0) {
        if (emptyMessage) emptyMessage.hidden = false;
        return;
      }
      if (emptyMessage) emptyMessage.hidden = true;

      items.forEach(function (item) {
        var li = document.createElement("li");
        li.className = "shopping-list__item" + (item.checked ? " shopping-list__item--checked" : "");

        var label = document.createElement("label");

        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = !!item.checked;
        checkbox.addEventListener("change", function () {
          toggleChecked(item.slug, checkbox.checked);
        });
        label.appendChild(checkbox);

        var text = document.createElement("span");
        text.textContent = item.name;
        label.appendChild(text);

        li.appendChild(label);

        var removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "chip__remove";
        removeBtn.setAttribute("aria-label", item.name + " öğesini sil");
        removeBtn.textContent = "×";
        removeBtn.addEventListener("click", function () {
          removeItem(item.slug);
        });
        li.appendChild(removeBtn);

        list.appendChild(li);
      });
    }

    function toggleChecked(slug, checked) {
      var items = getShopping().map(function (item) {
        if (item.slug === slug) {
          return { slug: item.slug, name: item.name, checked: checked };
        }
        return item;
      });
      setShopping(items);
      updateShoppingBadge();
      render();
    }

    function removeItem(slug) {
      var items = getShopping().filter(function (item) {
        return item.slug !== slug;
      });
      setShopping(items);
      updateShoppingBadge();
      render();
    }

    if (copyBtn) {
      copyBtn.addEventListener("click", function () {
        var items = getShopping();
        var text = items.map(function (item) { return "- " + item.name; }).join("\n");
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            copyBtn.textContent = "Kopyalandı ✓";
            window.setTimeout(function () { copyBtn.textContent = "Kopyala"; }, 1500);
          });
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        setShopping([]);
        updateShoppingBadge();
        render();
      });
    }

    render();
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateShoppingBadge();
    initHomePage();
    initDetailPage();
    initShoppingListPage();
  });
})();
