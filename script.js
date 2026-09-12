(() => {
    const header = document.querySelector('.site-header');
    const main = document.querySelector('main');
    const archive = document.querySelector('.earlier-highlights');
    const sectionLinks = [...document.querySelectorAll('.page-nav a')];
    const sections = sectionLinks.map(link => document.querySelector(link.hash));
    let framePending = false;

    // Native anchors handle navigation; this only marks the current section.
    function updateCurrentSection() {
        const marker = header.offsetHeight + 48;
        const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
        let currentSection = sections[0];

        for (const section of sections) {
            if (section.getBoundingClientRect().top <= marker) {
                currentSection = section;
            }
        }

        if (atBottom) {
            currentSection = sections[sections.length - 1];
        }

        for (const link of sectionLinks) {
            if (link.hash === `#${currentSection.id}`) {
                link.setAttribute('aria-current', 'location');
            } else {
                link.removeAttribute('aria-current');
            }
        }
        framePending = false;
    }

    function scheduleSectionUpdate() {
        if (framePending) return;
        framePending = true;
        requestAnimationFrame(updateCurrentSection);
    }

    window.addEventListener('scroll', scheduleSectionUpdate, { passive: true });
    window.addEventListener('resize', scheduleSectionUpdate);
    window.addEventListener('pageshow', scheduleSectionUpdate);
    archive.addEventListener('toggle', scheduleSectionUpdate);

    if ('ResizeObserver' in window) {
        new ResizeObserver(scheduleSectionUpdate).observe(main);
    }
    updateCurrentSection();

    // Print the complete archive, then restore the reader's screen state.
    let archiveWasOpen = archive.open;
    window.addEventListener('beforeprint', () => {
        archiveWasOpen = archive.open;
        archive.open = true;
    });
    window.addEventListener('afterprint', () => {
        archive.open = archiveWasOpen;
    });
})();
