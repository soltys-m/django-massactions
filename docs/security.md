# Security

* **Only registered keys are reachable.** The model, queryset, filter, queryset methods and form classes
  are never taken from the request. Unknown keys answer 404.
* **Authorization boundary.** `get_queryset()` and `restrict_queryset()` decide what a user can act on.
  Django model permissions (`<app>.<codename>_<model>`) and `has_permission()` gate the action itself.
  Both run before the selection is read.
* **Selection cookie.** The cookie is obfuscated (AES-ECB, the random key is appended to the value) so a
  client can produce any selection it likes. This is by design a convenience, not a trust boundary:
  the cookie can only name ids, and every id still has to pass `get_queryset()` and `restrict_queryset()`.
  Malformed cookies, invalid ids and stale ids are handled without errors.
* **Update action.** `field_name` must be declared in `update_fields`; `field_name_value` must be one of
  its `choices`. Values pass through the form field's `clean()`.
* **Redirects.** `back_url` is followed only when it points to the current host
  (`url_has_allowed_host_and_scheme`), otherwise `get_success_url()` is used.
* **Templates.** Object names are inserted as escaped HTML. Unlike crispy's `HTML` layout object, the
  library does not parse rendered content as a Django template.
* **Encrypt endpoint.** POST only, login required, CSRF protected.
