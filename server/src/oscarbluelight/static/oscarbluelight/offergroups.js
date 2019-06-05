/******/ (function(modules) { // webpackBootstrap
/******/ 	// install a JSONP callback for chunk loading
/******/ 	function webpackJsonpCallback(data) {
/******/ 		var chunkIds = data[0];
/******/ 		var moreModules = data[1];
/******/ 		var executeModules = data[2];
/******/
/******/ 		// add "moreModules" to the modules object,
/******/ 		// then flag all "chunkIds" as loaded and fire callback
/******/ 		var moduleId, chunkId, i = 0, resolves = [];
/******/ 		for(;i < chunkIds.length; i++) {
/******/ 			chunkId = chunkIds[i];
/******/ 			if(installedChunks[chunkId]) {
/******/ 				resolves.push(installedChunks[chunkId][0]);
/******/ 			}
/******/ 			installedChunks[chunkId] = 0;
/******/ 		}
/******/ 		for(moduleId in moreModules) {
/******/ 			if(Object.prototype.hasOwnProperty.call(moreModules, moduleId)) {
/******/ 				modules[moduleId] = moreModules[moduleId];
/******/ 			}
/******/ 		}
/******/ 		if(parentJsonpFunction) parentJsonpFunction(data);
/******/
/******/ 		while(resolves.length) {
/******/ 			resolves.shift()();
/******/ 		}
/******/
/******/ 		// add entry modules from loaded chunk to deferred list
/******/ 		deferredModules.push.apply(deferredModules, executeModules || []);
/******/
/******/ 		// run deferred modules when all chunks ready
/******/ 		return checkDeferredModules();
/******/ 	};
/******/ 	function checkDeferredModules() {
/******/ 		var result;
/******/ 		for(var i = 0; i < deferredModules.length; i++) {
/******/ 			var deferredModule = deferredModules[i];
/******/ 			var fulfilled = true;
/******/ 			for(var j = 1; j < deferredModule.length; j++) {
/******/ 				var depId = deferredModule[j];
/******/ 				if(installedChunks[depId] !== 0) fulfilled = false;
/******/ 			}
/******/ 			if(fulfilled) {
/******/ 				deferredModules.splice(i--, 1);
/******/ 				result = __webpack_require__(__webpack_require__.s = deferredModule[0]);
/******/ 			}
/******/ 		}
/******/
/******/ 		return result;
/******/ 	}
/******/
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// object to store loaded and loading chunks
/******/ 	// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 	// Promise = chunk loading, 0 = chunk loaded
/******/ 	var installedChunks = {
/******/ 		"offergroups": 0
/******/ 	};
/******/
/******/ 	var deferredModules = [];
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, { enumerable: true, get: getter });
/******/ 		}
/******/ 	};
/******/
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = function(exports) {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = __webpack_require__(value);
/******/ 		if(mode & 8) return value;
/******/ 		if((mode & 4) && typeof value === 'object' && value && value.__esModule) return value;
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		Object.defineProperty(ns, 'default', { enumerable: true, value: value });
/******/ 		if(mode & 2 && typeof value != 'string') for(var key in value) __webpack_require__.d(ns, key, function(key) { return value[key]; }.bind(null, key));
/******/ 		return ns;
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	var jsonpArray = window["webpackJsonp"] = window["webpackJsonp"] || [];
/******/ 	var oldJsonpFunction = jsonpArray.push.bind(jsonpArray);
/******/ 	jsonpArray.push = webpackJsonpCallback;
/******/ 	jsonpArray = jsonpArray.slice();
/******/ 	for(var i = 0; i < jsonpArray.length; i++) webpackJsonpCallback(jsonpArray[i]);
/******/ 	var parentJsonpFunction = oldJsonpFunction;
/******/
/******/
/******/ 	// add entry module to deferred list
/******/ 	deferredModules.push(["./src/offergroups.tsx","vendor"]);
/******/ 	// run deferred modules when ready
/******/ 	return checkDeferredModules();
/******/ })
/************************************************************************/
/******/ ({

/***/ "./src/offergroups.tsx":
/*!*****************************!*\
  !*** ./src/offergroups.tsx ***!
  \*****************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


Object.defineProperty(exports, "__esModule", {
  value: true
});

var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");

var react_dom_1 = __webpack_require__(/*! react-dom */ "./node_modules/react-dom/index.js");

var OfferGroupTable_1 = __webpack_require__(/*! ./offergroups/OfferGroupTable */ "./src/offergroups/OfferGroupTable.tsx");

var main = function main() {
  var elem = document.querySelector('#offergroup-table');
  var component = React.createElement(OfferGroupTable_1.default, {
    endpoint: elem.dataset.offergroupApi
  });
  react_dom_1.render(component, elem);
};

main();

/***/ }),

/***/ "./src/offergroups/OfferGroupTable.scss":
/*!**********************************************!*\
  !*** ./src/offergroups/OfferGroupTable.scss ***!
  \**********************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

// extracted by mini-css-extract-plugin

/***/ }),

/***/ "./src/offergroups/OfferGroupTable.tsx":
/*!*********************************************!*\
  !*** ./src/offergroups/OfferGroupTable.tsx ***!
  \*********************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


function _typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

Object.defineProperty(exports, "__esModule", {
  value: true
});

var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");

var classNames = __webpack_require__(/*! classnames */ "./node_modules/classnames/index.js");

var api_1 = __webpack_require__(/*! ../utils/api */ "./src/utils/api.ts");

__webpack_require__(/*! ./OfferGroupTable.scss */ "./src/offergroups/OfferGroupTable.scss");

var OfferGroupTable =
/*#__PURE__*/
function (_React$Component) {
  _inherits(OfferGroupTable, _React$Component);

  function OfferGroupTable(props) {
    var _this;

    _classCallCheck(this, OfferGroupTable);

    _this = _possibleConstructorReturn(this, _getPrototypeOf(OfferGroupTable).call(this, props));
    _this.state = {
      isLoading: true,
      groups: []
    };
    return _this;
  }

  _createClass(OfferGroupTable, [{
    key: "componentDidMount",
    value: function componentDidMount() {
      var _this2 = this;

      api_1.listOfferGroups(this.props.endpoint, function (err, resp) {
        if (err) {
          console.log(err);
          console.log(resp);
          return;
        }

        var groups = resp.body;

        _this2.setState({
          isLoading: false,
          groups: groups
        });
      });
    }
  }, {
    key: "buildGroupActions",
    value: function buildGroupActions(group) {
      var hasOffers = group.offers.length > 0;
      var isSystemGroup = group.is_system_group;
      var deleteClass = hasOffers || isSystemGroup ? 'disabled' : '';
      var deleteTitle;
      var deleteLink;

      if (isSystemGroup) {
        deleteTitle = 'System groups can not be deleted.';
      } else if (hasOffers) {
        deleteTitle = 'Remove all offers from this group to delete it.';
      } else {
        deleteTitle = "Delete the ".concat(group.name, " offer group");
        deleteLink = group.delete_link;
      }

      return React.createElement("div", {
        className: "btn-toolbar"
      }, React.createElement("div", {
        className: "btn-group"
      }, React.createElement("button", {
        className: "btn btn-default dropdown-toggle",
        type: "button",
        "data-toggle": "dropdown",
        "aria-expanded": "true"
      }, "Actions ", React.createElement("span", {
        className: "caret"
      })), React.createElement("ul", {
        className: "dropdown-menu pull-right"
      }, React.createElement("li", null, React.createElement("a", {
        href: group.update_link,
        title: "Edit the details of the ".concat(group.name, " offer group")
      }, "Edit")), React.createElement("li", {
        className: deleteClass,
        title: deleteTitle
      }, React.createElement("a", {
        href: deleteLink
      }, "Delete")))));
    }
  }, {
    key: "buildBooleanLabel",
    value: function buildBooleanLabel(truthy) {
      var dangerousNo = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      if (truthy) {
        return React.createElement("span", {
          className: "label label-success"
        }, "Yes");
      }

      var intent = dangerousNo ? 'label-danger' : 'label-default';
      return React.createElement("span", {
        className: "label ".concat(intent)
      }, "No");
    }
  }, {
    key: "buildOfferRow",
    value: function buildOfferRow(index, offer) {
      var itemClasses = classNames({
        'offergroup__offer': true,
        'offergroup__offer--inactive': !offer.is_available
      });
      return React.createElement("tr", {
        key: "offer-".concat(offer.id),
        className: itemClasses
      }, React.createElement("td", {
        className: "offergroup__offer__index"
      }, React.createElement("a", {
        href: offer.details_link
      }, index)), React.createElement("td", {
        className: "offergroup__offer__name"
      }, React.createElement("a", {
        href: offer.details_link
      }, offer.name)), React.createElement("td", {
        className: "offergroup__offer__priority"
      }, offer.priority), React.createElement("td", {
        className: "offergroup__offer__type"
      }, React.createElement("span", {
        className: "label label-info"
      }, "Offer")));
    }
  }, {
    key: "buildVoucherRow",
    value: function buildVoucherRow(index, offer) {
      var elems = offer.vouchers.map(function (voucher) {
        var itemClasses = classNames({
          'offergroup__voucher': true,
          'offergroup__voucher--inactive': !voucher.is_active
        });
        return React.createElement("tr", {
          key: "voucher-".concat(voucher.id),
          className: itemClasses
        }, React.createElement("td", {
          className: "offergroup__voucher__index"
        }, React.createElement("a", {
          href: voucher.details_link
        }, index)), React.createElement("td", {
          className: "offergroup__voucher__name"
        }, React.createElement("a", {
          href: voucher.details_link
        }, voucher.name)), React.createElement("td", {
          className: "offergroup__voucher__priority"
        }, offer.priority), React.createElement("td", {
          className: "offergroup__voucher__type"
        }, React.createElement("span", {
          className: "label label-success"
        }, "Voucher")));
      });
      return elems;
    }
  }, {
    key: "buildOfferList",
    value: function buildOfferList(group) {
      var self = this;
      var rows = group.offers.map(function (offer, i) {
        var index = i + 1;
        return offer.vouchers.length > 0 ? self.buildVoucherRow(index, offer) : self.buildOfferRow(index, offer);
      });
      return React.createElement("table", {
        className: "table table-bordered table-striped offergroup-subtable"
      }, React.createElement("caption", null, group.name), React.createElement("thead", null, React.createElement("tr", null, React.createElement("th", {
        className: "offergroup__offer__index"
      }, "#"), React.createElement("th", {
        className: "offergroup__offer__name"
      }, "Name"), React.createElement("th", {
        className: "offergroup__offer__priority"
      }, "Priority"), React.createElement("th", {
        className: "offergroup__offer__type"
      }, "Type"))), React.createElement("tbody", null, rows));
    }
  }, {
    key: "buildGroupRows",
    value: function buildGroupRows() {
      var _this3 = this;

      var self = this;
      var numCols = 5;

      if (this.state.isLoading) {
        return React.createElement("tr", null, React.createElement("td", {
          colSpan: numCols,
          className: "offergroup__empty"
        }, "Loading\u2026"));
      }

      if (this.state.groups.length <= 0) {
        return React.createElement("tr", null, React.createElement("td", {
          colSpan: numCols,
          className: "offergroup__empty"
        }, "No Offer Groups found."));
      }

      return this.state.groups.map(function (group) {
        return React.createElement("tr", {
          key: group.id,
          "data-group-slug": group.slug
        }, React.createElement("td", null, group.name), React.createElement("td", null, _this3.buildBooleanLabel(group.is_system_group)), React.createElement("td", null, group.priority), React.createElement("td", {
          className: "subtable-container"
        }, self.buildOfferList(group)), React.createElement("td", null, self.buildGroupActions(group)));
      });
    }
  }, {
    key: "render",
    value: function render() {
      return React.createElement("table", {
        className: "table table-bordered"
      }, React.createElement("caption", null, React.createElement("i", {
        className: "icon-gift icon-large"
      })), React.createElement("tbody", null, React.createElement("tr", null, React.createElement("th", null, "Name"), React.createElement("th", null, "Is System Group?"), React.createElement("th", null, "Priority"), React.createElement("th", null, "Group Contents"), React.createElement("th", null, "Actions")), this.buildGroupRows()));
    }
  }]);

  return OfferGroupTable;
}(React.Component);

exports.default = OfferGroupTable;

/***/ }),

/***/ "./src/utils/api.ts":
/*!**************************!*\
  !*** ./src/utils/api.ts ***!
  \**************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


Object.defineProperty(exports, "__esModule", {
  value: true
});

var request = __webpack_require__(/*! superagent */ "./node_modules/superagent/lib/client.js");

exports.listOfferGroups = function () {
  var endpoint = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : '/dashboard/offers/api/offergroups/';
  var callback = arguments.length > 1 ? arguments[1] : undefined;
  return request.get(endpoint).set('Accept', 'application/json').end(callback);
};

/***/ })

/******/ });
//# sourceMappingURL=offergroups.js.map