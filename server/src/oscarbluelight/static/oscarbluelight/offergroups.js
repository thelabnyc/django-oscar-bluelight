!(function () {
  var e,
    t = {
      2333: function (e, t, r) {
        "use strict";
        r(5306),
          r(4197),
          r(6495),
          r(7145),
          r(5109),
          r(5125),
          r(2472),
          r(9743),
          r(8255),
          r(9135),
          r(8145),
          r(5206),
          r(4633),
          r(285),
          r(3753),
          r(1637);
        var n = r(7015),
          a = r(6031),
          o = r(3616),
          l = r(3932),
          s = r.n(l),
          c = r(5637),
          u = r.n(c);
        class i extends n.Component {
          constructor(e) {
            super(e), (this.state = { isLoading: !0, groups: [] });
          }
          componentDidMount() {
            return (0, o.mG)(this, void 0, void 0, function* () {
              const e = yield ((e = "/dashboard/offers/api/offergroups/") =>
                (0, o.mG)(void 0, void 0, void 0, function* () {
                  return (yield u()
                    .get(e)
                    .set("Accept", "application/json")).body;
                }))(this.props.endpoint);
              this.setState({ isLoading: !1, groups: e });
            });
          }
          buildGroupActions(e) {
            const t = e.offers.length > 0,
              r = e.is_system_group,
              a = t || r ? "disabled" : "";
            let o, l;
            return (
              r
                ? (o = gettext("System groups can not be deleted."))
                : t
                ? (o = gettext(
                    "Remove all offers from this group to delete it."
                  ))
                : ((o = interpolate(gettext("Delete the %s offer group"), [
                    e.name,
                  ])),
                  (l = e.delete_link)),
              n.createElement(
                "div",
                { className: "btn-toolbar" },
                n.createElement(
                  "div",
                  { className: "dropdown" },
                  n.createElement(
                    "button",
                    {
                      className: "btn btn-secondary dropdown-toggle",
                      type: "button",
                      "data-toggle": "dropdown",
                      "aria-haspopup": "true",
                      "aria-expanded": "false",
                    },
                    gettext("Actions")
                  ),
                  n.createElement(
                    "ul",
                    { className: "dropdown-menu dropdown-menu-right" },
                    n.createElement(
                      "a",
                      {
                        className: "dropdown-item",
                        href: e.update_link,
                        title: interpolate(
                          gettext("Edit the details of the %s offer group"),
                          [e.name]
                        ),
                      },
                      gettext("Edit")
                    ),
                    n.createElement(
                      "a",
                      { className: `dropdown-item ${a}`, title: o, href: l },
                      gettext("Delete")
                    )
                  )
                )
              )
            );
          }
          buildBooleanLabel(e, t = !1) {
            if (e)
              return n.createElement(
                "span",
                { className: "label label-success" },
                gettext("Yes")
              );
            const r = t ? "label-danger" : "label-default";
            return n.createElement(
              "span",
              { className: `label ${r}` },
              gettext("No")
            );
          }
          buildOfferRow(e, t) {
            const r = s()({
              offergroup__offer: !0,
              "offergroup__offer--inactive": !t.is_available,
            });
            return n.createElement(
              "tr",
              { key: `offer-${t.id}`, className: r },
              n.createElement(
                "td",
                { className: "offergroup__offer__index" },
                n.createElement("a", { href: t.details_link }, e)
              ),
              n.createElement(
                "td",
                { className: "offergroup__offer__name" },
                n.createElement("a", { href: t.details_link }, t.name)
              ),
              n.createElement(
                "td",
                { className: "offergroup__offer__priority" },
                t.priority
              ),
              n.createElement(
                "td",
                { className: "offergroup__offer__type" },
                n.createElement(
                  "span",
                  { className: "label label-info" },
                  gettext("Offer")
                )
              )
            );
          }
          buildVoucherRow(e, t) {
            return t.vouchers.map((r) => {
              const a = s()({
                offergroup__voucher: !0,
                "offergroup__voucher--inactive": !r.is_active,
              });
              return n.createElement(
                "tr",
                { key: `voucher-${r.id}`, className: a },
                n.createElement(
                  "td",
                  { className: "offergroup__voucher__index" },
                  n.createElement("a", { href: r.details_link }, e)
                ),
                n.createElement(
                  "td",
                  { className: "offergroup__voucher__name" },
                  n.createElement("a", { href: r.details_link }, r.name)
                ),
                n.createElement(
                  "td",
                  { className: "offergroup__voucher__priority" },
                  t.priority
                ),
                n.createElement(
                  "td",
                  { className: "offergroup__voucher__type" },
                  n.createElement(
                    "span",
                    { className: "label label-success" },
                    gettext("Voucher")
                  )
                )
              );
            });
          }
          buildOfferList(e) {
            const t = this,
              r = e.offers
                .filter(
                  (e) => !("Voucher" === e.offer_type && e.vouchers.length <= 0)
                )
                .map((e, r) => {
                  const n = r + 1;
                  return e.vouchers.length > 0
                    ? t.buildVoucherRow(n, e)
                    : t.buildOfferRow(n, e);
                });
            return n.createElement(
              "table",
              {
                className:
                  "table table-bordered table-striped offergroup-subtable",
              },
              n.createElement("caption", null, e.name),
              n.createElement(
                "thead",
                null,
                n.createElement(
                  "tr",
                  null,
                  n.createElement(
                    "th",
                    { className: "offergroup__offer__index" },
                    gettext("#")
                  ),
                  n.createElement(
                    "th",
                    { className: "offergroup__offer__name" },
                    gettext("Name")
                  ),
                  n.createElement(
                    "th",
                    { className: "offergroup__offer__priority" },
                    gettext("Priority")
                  ),
                  n.createElement(
                    "th",
                    { className: "offergroup__offer__type" },
                    gettext("Type")
                  )
                )
              ),
              n.createElement("tbody", null, r)
            );
          }
          buildGroupRows() {
            const e = this;
            return this.state.isLoading
              ? n.createElement(
                  "tr",
                  null,
                  n.createElement(
                    "td",
                    { colSpan: 5, className: "offergroup__empty" },
                    gettext("Loading…")
                  )
                )
              : this.state.groups.length <= 0
              ? n.createElement(
                  "tr",
                  null,
                  n.createElement(
                    "td",
                    { colSpan: 5, className: "offergroup__empty" },
                    gettext("No Offer Groups found.")
                  )
                )
              : this.state.groups.map((t) =>
                  n.createElement(
                    "tr",
                    { key: t.id, "data-group-slug": t.slug },
                    n.createElement("td", null, t.name),
                    n.createElement(
                      "td",
                      null,
                      this.buildBooleanLabel(t.is_system_group)
                    ),
                    n.createElement("td", null, t.priority),
                    n.createElement(
                      "td",
                      { className: "subtable-container" },
                      e.buildOfferList(t)
                    ),
                    n.createElement("td", null, e.buildGroupActions(t))
                  )
                );
          }
          render() {
            return n.createElement(
              "table",
              { className: "table table-bordered" },
              n.createElement(
                "caption",
                null,
                n.createElement("i", { className: "fas fa-gift" })
              ),
              n.createElement(
                "tbody",
                null,
                n.createElement(
                  "tr",
                  null,
                  n.createElement("th", null, gettext("Name")),
                  n.createElement("th", null, gettext("Is System Group?")),
                  n.createElement("th", null, gettext("Priority")),
                  n.createElement("th", null, gettext("Group Contents")),
                  n.createElement("th", null, gettext("Actions"))
                ),
                this.buildGroupRows()
              )
            );
          }
        }
        var f = i;
        !(function () {
          const e = document.querySelector("#offergroup-table"),
            t = n.createElement(f, { endpoint: e.dataset.offergroupApi || "" });
          (0, a.render)(t, e);
        })();
      },
      4654: function () {},
    },
    r = {};
  function n(e) {
    var a = r[e];
    if (void 0 !== a) return a.exports;
    var o = (r[e] = { exports: {} });
    return t[e](o, o.exports, n), o.exports;
  }
  (n.m = t),
    (e = []),
    (n.O = function (t, r, a, o) {
      if (!r) {
        var l = 1 / 0;
        for (u = 0; u < e.length; u++) {
          (r = e[u][0]), (a = e[u][1]), (o = e[u][2]);
          for (var s = !0, c = 0; c < r.length; c++)
            (!1 & o || l >= o) &&
            Object.keys(n.O).every(function (e) {
              return n.O[e](r[c]);
            })
              ? r.splice(c--, 1)
              : ((s = !1), o < l && (l = o));
          s && (e.splice(u--, 1), (t = a()));
        }
        return t;
      }
      o = o || 0;
      for (var u = e.length; u > 0 && e[u - 1][2] > o; u--) e[u] = e[u - 1];
      e[u] = [r, a, o];
    }),
    (n.n = function (e) {
      var t =
        e && e.__esModule
          ? function () {
              return e.default;
            }
          : function () {
              return e;
            };
      return n.d(t, { a: t }), t;
    }),
    (n.d = function (e, t) {
      for (var r in t)
        n.o(t, r) &&
          !n.o(e, r) &&
          Object.defineProperty(e, r, { enumerable: !0, get: t[r] });
    }),
    (n.g = (function () {
      if ("object" == typeof globalThis) return globalThis;
      try {
        return this || new Function("return this")();
      } catch (e) {
        if ("object" == typeof window) return window;
      }
    })()),
    (n.o = function (e, t) {
      return Object.prototype.hasOwnProperty.call(e, t);
    }),
    (function () {
      var e = { 583: 0 };
      n.O.j = function (t) {
        return 0 === e[t];
      };
      var t = function (t, r) {
          var a,
            o,
            l = r[0],
            s = r[1],
            c = r[2],
            u = 0;
          for (a in s) n.o(s, a) && (n.m[a] = s[a]);
          if (c) var i = c(n);
          for (t && t(r); u < l.length; u++)
            (o = l[u]), n.o(e, o) && e[o] && e[o][0](), (e[l[u]] = 0);
          return n.O(i);
        },
        r = (self.webpackChunkdjango_oscar_bluelight =
          self.webpackChunkdjango_oscar_bluelight || []);
      r.forEach(t.bind(null, 0)), (r.push = t.bind(null, r.push.bind(r)));
    })();
  var a = n.O(void 0, [736], function () {
    return n(2333);
  });
  a = n.O(a);
})();
//# sourceMappingURL=offergroups.js.map
