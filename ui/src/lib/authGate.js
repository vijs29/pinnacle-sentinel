// Whether a page that needs a login should send the visitor to /login.
// `isDev` is Vite's import.meta.env.DEV: true only under the local `npm run dev` server and
// false in every production build (the bundler removes the dev branch entirely), so this
// can only relax the gate on a developer's own machine, never on the live site.
export function shouldRedirectToLogin(token, isDev) {
  return !token && !isDev
}

// Headers for an API call: the login token when there is one, nothing when there is not.
export function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}
