// Редактор тегов-чипов. Каждый чип = видимая метка + скрытый input
// name="tags" (уходит на сервер списком) + кнопка удаления. Работает и с
// чипами, отрисованными сервером (edit-форма), и с добавленными на клиенте.
(function () {
  "use strict";

  function initEditor(editor) {
    var list = editor.querySelector(".tag-editor-list");
    var input = editor.querySelector(".tag-editor-input");
    var addBtn = editor.querySelector(".tag-editor-btn");
    if (!list || !input || !addBtn) return;

    function existingNames() {
      var hidden = list.querySelectorAll('input[type="hidden"]');
      return Array.prototype.map.call(hidden, function (el) {
        return el.value.toLowerCase();
      });
    }

    function addChip(rawName) {
      var name = rawName.trim();
      if (!name) return;
      // Дубли (без учёта регистра) игнорируем — сервер их всё равно схлопнет.
      if (existingNames().indexOf(name.toLowerCase()) !== -1) {
        input.value = "";
        return;
      }

      var chip = document.createElement("span");
      chip.className = "tag-chip";

      var label = document.createElement("span");
      label.className = "tag-chip-label";
      label.textContent = name;

      var hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "tags";
      hidden.value = name;

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "tag-chip-x";
      remove.setAttribute("aria-label", "Удалить тег");
      remove.textContent = "×"; // ×

      chip.appendChild(label);
      chip.appendChild(hidden);
      chip.appendChild(remove);
      list.appendChild(chip);
      input.value = "";
    }

    addBtn.addEventListener("click", function () {
      addChip(input.value);
      input.focus();
    });

    // Enter или запятая добавляют тег, не отправляя форму.
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        addChip(input.value);
      }
    });

    // Делегирование: ловим клик по крестику любого чипа (в т.ч. серверного).
    list.addEventListener("click", function (e) {
      var btn = e.target.closest(".tag-chip-x");
      if (btn) {
        btn.closest(".tag-chip").remove();
      }
    });
  }

  // Формы с [data-autosubmit] отправляются сразу при изменении любого
  // select/input — без отдельной кнопки «Применить».
  function initAutoSubmit(form) {
    form.addEventListener("change", function () {
      form.submit();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var editors = document.querySelectorAll("[data-tag-editor]");
    Array.prototype.forEach.call(editors, initEditor);

    var forms = document.querySelectorAll("form[data-autosubmit]");
    Array.prototype.forEach.call(forms, initAutoSubmit);
  });
})();
