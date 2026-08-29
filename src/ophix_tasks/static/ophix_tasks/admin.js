(function () {
    'use strict';

    var SCROLL_KEY = 'ophix-tasks-schedule-scroll';

    // -----------------------------------------------------------------------
    // Restore scroll position after a popup-triggered page reload
    // -----------------------------------------------------------------------
    var savedScroll = sessionStorage.getItem(SCROLL_KEY);
    if (savedScroll !== null) {
        sessionStorage.removeItem(SCROLL_KEY);
        window.addEventListener('load', function () {
            window.scrollTo(0, parseInt(savedScroll, 10));
        });
    }

    // -----------------------------------------------------------------------
    // Add an "Add task" link below the tasks table
    // -----------------------------------------------------------------------
    function addAddTaskLink(group, scheduleId) {
        if (group.dataset.addLinkAdded) return;
        group.dataset.addLinkAdded = '1';

        var url = '/admin/ophix_tasks/scheduledtask/add/?schedule=' + scheduleId + '&_popup=1';

        var link = document.createElement('a');
        link.className = 'addlink';
        link.textContent = 'Add Task';
        link.href = url;
        link.setAttribute('onclick', 'return showRelatedObjectPopup(this);');

        // Insert as a proper add-row inside the table so it gets Django's
        // standard grey-bar styling, matching "Add another X" on other inlines.
        // Use group.querySelector('table') rather than '.tabular table' because
        // the collapse class wraps the table inside <details>, breaking the
        // more specific selector in some Django versions.
        var table = group.querySelector('table');
        var tbody = table && (table.querySelector('tbody') || table);
        if (tbody) {
            var tr = document.createElement('tr');
            tr.className = 'add-row';
            var td = document.createElement('td');
            td.setAttribute('colspan', '100');
            td.appendChild(link);
            tr.appendChild(td);
            tbody.appendChild(tr);
        } else {
            group.appendChild(link);
        }
    }

    // -----------------------------------------------------------------------
    // After any popup save, close the popup and reload to refresh the list.
    //
    // We do NOT call the original Django handlers here. Both
    // dismissAddRelatedObjectPopup and dismissChangeRelatedObjectPopup are
    // designed to update a FK <select> widget (via SelectBox) after adding or
    // editing a related object. On this page there are no FK select widgets,
    // so calling them either crashes (SelectBox not defined) or does nothing
    // useful. We own the popup lifecycle here: close it and reload.
    //
    // django-admin-interface renders popups as <dialog> elements. Calling
    // win.close() closes the inner window/frame but leaves the <dialog> open.
    // We close all open <dialog> elements explicitly from the parent side.
    // -----------------------------------------------------------------------
    function closePendingPopups(win) {
        try { win.close(); } catch (e) {}
        document.querySelectorAll('dialog[open]').forEach(function (d) {
            try { d.close(); } catch (e) {}
        });
    }

    function installPopupReloadHooks() {
        window.dismissChangeRelatedObjectPopup = function (win, objId, objRepr, objAction) {
            closePendingPopups(win);
            sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
            window.location.reload();
        };

        window.dismissAddRelatedObjectPopup = function (win, newId, newRepr, newValue) {
            closePendingPopups(win);
            sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
            window.location.reload();
        };
    }

    // -----------------------------------------------------------------------
    // Interval help — ScheduledTask change form.
    // When a scheduler is selected, replace the interval field help text with
    // the scheduler's interval_help string (stored as data-interval-help on
    // each <option> by the SchedulerSelect widget).
    // -----------------------------------------------------------------------
    function initIntervalHelp() {
        var schedulerEl = document.getElementById('id_scheduler');
        if (!schedulerEl) return;

        var intervalField = document.querySelector('.field-interval');
        if (!intervalField) return;

        var helpEl = intervalField.querySelector('.help');
        var defaultText = helpEl ? helpEl.textContent : '';

        // Create a help element if the interval field has none (no static help_text).
        if (!helpEl) {
            helpEl = document.createElement('p');
            helpEl.className = 'help';
            intervalField.appendChild(helpEl);
        }

        function update() {
            var selected = schedulerEl.options[schedulerEl.selectedIndex];
            var text = selected && selected.dataset.intervalHelp;
            helpEl.textContent = text || defaultText;
            helpEl.style.whiteSpace = text ? 'pre-line' : '';
        }

        // #id_scheduler is an FK <select> inside .related-widget-wrapper, so
        // admin-interface's select2-init.js auto-upgrades it to Select2 (it's not
        // in autocomplete_fields). Select2 reports a selection change purely via
        // jQuery's .trigger('change') — there is no native .change() method on a
        // <select> for jQuery to invoke, so nothing dispatches a real DOM event,
        // and a plain addEventListener('change', ...) never fires. Bind through
        // jQuery's .on('change', ...) when available (it still catches genuine
        // native events too), falling back to addEventListener only if jQuery
        // isn't present at all.
        if (window.jQuery) {
            window.jQuery(schedulerEl).on('change', update);
        } else {
            schedulerEl.addEventListener('change', update);
        }
        update();
    }

    // -----------------------------------------------------------------------
    // Inline checkbox auto-save — enabled/paused toggles in the tasks inline.
    //
    // Fires a POST to the toggle endpoint immediately when a checkbox changes,
    // so the operator does not need to save the whole Schedule form just to
    // pause or re-enable an individual task.
    // -----------------------------------------------------------------------
    function initInlineToggles(group) {
        var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput) return;

        group.addEventListener('change', function (e) {
            var cb = e.target;
            if (cb.tagName !== 'INPUT' || cb.type !== 'checkbox') return;

            var nameMatch = cb.name.match(/^tasks-(\d+)-(enabled|paused)$/);
            if (!nameMatch) return;

            var idx = nameMatch[1];
            var field = nameMatch[2];

            var idInput = group.querySelector('input[name="tasks-' + idx + '-id"]');
            if (!idInput || !idInput.value) return;

            var pk = idInput.value;
            var value = cb.checked ? '1' : '0';

            fetch('/admin/ophix_tasks/scheduledtask/' + pk + '/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfInput.value,
                },
                body: 'field=' + encodeURIComponent(field) + '&value=' + value,
            }).catch(function () {});
        });
    }

    // -----------------------------------------------------------------------
    // Output handling warning — ScheduledTask change form.
    // When stdout_handling=file and stderr_handling=report are both selected,
    // stdout is silently discarded (not written to the log file) due to shell
    // pipe ordering constraints. Warn the operator before they save.
    // -----------------------------------------------------------------------
    function initOutputWarning() {
        var stdoutEl = document.getElementById('id_stdout_handling');
        var stderrEl = document.getElementById('id_stderr_handling');
        if (!stdoutEl || !stderrEl) return;

        var fieldset = stdoutEl.closest('fieldset');
        if (!fieldset) return;

        var warning = document.createElement('p');
        warning.className = 'help';
        warning.style.cssText = 'color: var(--ophix-paused-color, #b45309); font-weight: bold; display: none;';
        warning.textContent = (
            'Warning: stdout=file has no effect when stderr=report. ' +
            'Shell pipe ordering means stdout is always discarded in this combination — ' +
            'the log file will not be written. ' +
            'To capture both streams, use stdout=report with stderr=report or merge (interleaved), ' +
            'or use stderr=file with stdout=report (separate destinations), ' +
            'or set both to inherit and write the full redirect in the command field.'
        );

        var logFileField = fieldset.querySelector('.field-log_file');
        if (logFileField) {
            logFileField.insertAdjacentElement('afterend', warning);
        } else {
            fieldset.appendChild(warning);
        }

        function update() {
            var bad = stdoutEl.value === 'file' && stderrEl.value === 'report';
            warning.style.display = bad ? '' : 'none';
        }

        stdoutEl.addEventListener('change', update);
        stderrEl.addEventListener('change', update);
        update();
    }

    // -----------------------------------------------------------------------
    // Main — locate the group via the formset management input.
    // TabularInline rows are <tr> elements, not .inline-related divs, so
    // class-based selectors used for StackedInline won't work here.
    // id_tasks-TOTAL_FORMS is always present in the Schedule change form.
    // -----------------------------------------------------------------------
    // -----------------------------------------------------------------------
    // Compact toggle — ScheduledTask list view.
    // Hides non-essential columns; preference persisted in localStorage.
    // -----------------------------------------------------------------------
    function initCompactToggle() {
        var btn = document.getElementById('compact-toggle');
        if (!btn) return;

        var COMPACT_KEY = 'ophix-tasks-scheduledtask-compact';

        function apply(compact) {
            if (compact) {
                document.body.classList.add('compact');
                btn.textContent = 'Full View';
            } else {
                document.body.classList.remove('compact');
                btn.textContent = 'Compact';
            }
        }

        apply(localStorage.getItem(COMPACT_KEY) === '1');

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var compact = !document.body.classList.contains('compact');
            localStorage.setItem(COMPACT_KEY, compact ? '1' : '0');
            apply(compact);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initCompactToggle();
        initIntervalHelp();
        initOutputWarning();
        var mgmt = document.getElementById('id_tasks-TOTAL_FORMS');
        if (!mgmt) return;

        var group = mgmt.closest('.inline-group');
        if (!group) return;

        // Tag the group so CSS can target it without relying on a generated id
        group.classList.add('ophix-tasks-inline');

        initInlineToggles(group);

        // Extract Schedule PK from the URL: /admin/ophix_tasks/schedule/<pk>/change/
        var match = window.location.pathname.match(/\/(\d+)\/change\//);
        if (match) {
            addAddTaskLink(group, match[1]);
        }

        installPopupReloadHooks();
    });
})();
