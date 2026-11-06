/**
 * Aurevia Motors — Interactive Behaviors
 */

document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for in-page anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId && targetId.length > 1) {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // Mobile Hamburger Navigation Drawer
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
            navToggle.setAttribute('aria-expanded', !isExpanded);
            navToggle.classList.toggle('active');
            navMenu.classList.toggle('nav-menu-open');
        });

        // Close mobile drawer when clicking a link
        navMenu.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navToggle.setAttribute('aria-expanded', 'false');
                navToggle.classList.remove('active');
                navMenu.classList.remove('nav-menu-open');
            });
        });
    }

    // Interactive Media Gallery Thumbnail Switcher
    const activeImage = document.getElementById('active-gallery-image');
    const thumbnailBtns = document.querySelectorAll('.thumbnail-btn');

    if (activeImage && thumbnailBtns.length > 0) {
        thumbnailBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const newSrc = this.getAttribute('data-img-src');
                if (newSrc && activeImage.src !== newSrc) {
                    // Smooth cross-fade transition
                    activeImage.style.opacity = '0.3';
                    setTimeout(() => {
                        activeImage.src = newSrc;
                        activeImage.style.opacity = '1';
                    }, 150);

                    thumbnailBtns.forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                }
            });
        });
    }

    // Reservation / Add-to-cart boundary feedback
    const acquireBtn = document.getElementById('btn-acquire-action');
    if (acquireBtn) {
        acquireBtn.addEventListener('click', function () {
            alert('Aurevia Atelier Reservation: Online cart, digital tokenization, and checkout pipelines will be activated in Phase 06.');
        });
    }

    // Console branding message
    console.log(
        '%c AUREVIA MOTORS %c Luxury Supercar Atelier & Digital Showroom Initialized ',
        'background: #d4af37; color: #0a0c10; font-weight: bold; padding: 4px 8px; border-radius: 2px;',
        'background: #181d28; color: #f0f3f6; padding: 4px 8px;'
    );
});
