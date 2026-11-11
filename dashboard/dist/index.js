// No web-dashboard UI: this manifest exists to mount plugin_api.py for the Desktop "Workshop" screen (ctx.rest).
(function () {
  var plugins = window.__HERMES_PLUGINS__
  if (plugins && typeof plugins.register === 'function') {
    plugins.register('home-3d-workshop', function WorkshopDashboardPlaceholder() { return null })
  }
})()
