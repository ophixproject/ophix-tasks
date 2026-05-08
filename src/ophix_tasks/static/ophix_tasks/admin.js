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
        link.textContent = 'Add task';
        link.href = url;
        link.style.cssText = 'display: inline-block; padding: 0.5em 1em;';
        // Use the same mechanism as the Edit links — showRelatedObjectPopup returns
        // false, which prevents both the default navigation and Django's own click
        // interceptor from double-opening the dialog.
        link.setAttribute('onclick', 'return showRelatedObjectPopup(this);');

        // Insert after the .tabular wrapper (where Django normally puts "Add another")
        var tabular = group.querySelector('.tabular');
        if (tabular) {
            tabular.insertAdjacentElement('afterend', link);
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

        schedulerEl.addEventListener('change', update);
        update();
    }

    // -----------------------------------------------------------------------
    // Main — locate the group via the formset management input.
    // TabularInline rows are <tr> elements, not .inline-related divs, so
    // class-based selectors used for StackedInline won't work here.
    // id_tasks-TOTAL_FORMS is always present in the Schedule change form.
    // -----------------------------------------------------------------------
    document.addEventListener('DOMContentLoaded', function () {
        initIntervalHelp();
        var mgmt = document.getElementById('id_tasks-TOTAL_FORMS');
        if (!mgmt) return;

        var group = mgmt.closest('.inline-group');
        if (!group) return;

        // Tag the group so CSS can target it without relying on a generated id
        group.classList.add('ophix-tasks-inline');

        // Extract Schedule PK from the URL: /admin/ophix_tasks/schedule/<pk>/change/
        var match = window.location.pathname.match(/\/(\d+)\/change\//);
        if (match) {
            addAddTaskLink(group, match[1]);
        }

        installPopupReloadHooks();
    });
})();
