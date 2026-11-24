(function () {
  // 1. Restore saved light/dark theme
  try {
    var saved = localStorage.getItem('theme')
    if (saved === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark')
    } else if (saved === 'light') {
      document.documentElement.removeAttribute('data-theme')
    }
  } catch (e) {}

  // 2. Theme toggle button (#theme-toggle)
  var toggle = document.getElementById('theme-toggle')
  if (toggle) {
    toggle.addEventListener('click', function (e) {
      e.preventDefault()
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark'
      if (isDark) {
        document.documentElement.removeAttribute('data-theme')
        try { localStorage.setItem('theme', 'light') } catch (err) {}
      } else {
        document.documentElement.setAttribute('data-theme', 'dark')
        try { localStorage.setItem('theme', 'dark') } catch (err) {}
      }
    })
  }

  // 3. Mobile hamburger menu button
  var navBtn = document.querySelector('.ldas-nav__toggle, .greedy-nav > button')
  if (navBtn) {
    navBtn.addEventListener('click', function () {
      var list = document.getElementById('ldas-nav-list') || document.querySelector('.greedy-nav .visible-links')
      if (!list) return
      var open = list.classList.toggle('is-open')
      navBtn.setAttribute('aria-expanded', open ? 'true' : 'false')
    })
  }

  // 4. Keep profile card only on home (/ and /ja/) even in cached previews
  var path = window.location.pathname.replace(/\/+$/, '') || '/'
  if (path !== '/' && path !== '/ja' && path !== '/index.html' && path !== '/ja/index.html') {
    document.querySelectorAll('.sidebar').forEach(function (el) {
      el.style.display = 'none'
    })
  }
})()
