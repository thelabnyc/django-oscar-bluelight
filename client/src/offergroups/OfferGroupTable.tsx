import React from "react";
import classNames from "classnames";
import { listOfferGroups } from "../utils/api";
import { IOfferGroup, IOffer } from "../utils/api.interfaces";

import "./OfferGroupTable.scss";

export interface IProps {
    endpoint: string;
}

export interface IState {
    isLoading: boolean;
    groups: IOfferGroup[];
}

class OfferGroupTable extends React.Component<IProps, IState> {
    constructor(props: IProps) {
        super(props);
        this.state = {
            isLoading: true,
            groups: [],
        };
    }

    componentDidMount() {
        const load = async () => {
            const groups = await listOfferGroups(this.props.endpoint);
            this.setState({
                isLoading: false,
                groups: groups,
            });
        };
        load().catch(console.log);
    }

    private buildGroupActions(group: IOfferGroup) {
        const hasOffers = group.offers.length > 0;
        const isSystemGroup = group.is_system_group;

        const deleteClass = hasOffers || isSystemGroup ? "disabled" : "";

        let deleteTitle: string;
        let deleteLink: string | undefined = undefined;
        if (isSystemGroup) {
            deleteTitle = gettext("System groups can not be deleted.");
        } else if (hasOffers) {
            deleteTitle = gettext(
                "Remove all offers from this group to delete it.",
            );
        } else {
            deleteTitle = interpolate(gettext("Delete the %s offer group"), [
                group.name,
            ]);
            deleteLink = group.delete_link;
        }

        return (
            <div className="btn-toolbar">
                <div className="dropdown">
                    <button
                        className="btn btn-secondary dropdown-toggle"
                        type="button"
                        data-toggle="dropdown"
                        aria-haspopup="true"
                        aria-expanded="false"
                    >
                        {gettext("Actions")}
                    </button>
                    <ul className="dropdown-menu dropdown-menu-right">
                        <a
                            className="dropdown-item"
                            href={group.update_link}
                            title={interpolate(
                                gettext(
                                    "Edit the details of the %s offer group",
                                ),
                                [group.name],
                            )}
                        >
                            {gettext("Edit")}
                        </a>
                        <a
                            className={`dropdown-item ${deleteClass}`}
                            title={deleteTitle}
                            href={deleteLink}
                        >
                            {gettext("Delete")}
                        </a>
                    </ul>
                </div>
            </div>
        );
    }

    private buildBooleanLabel(truthy: boolean, dangerousNo = false) {
        if (truthy) {
            return (
                <span className="label label-success">{gettext("Yes")}</span>
            );
        }
        const intent = dangerousNo ? "label-danger" : "label-default";
        return <span className={`label ${intent}`}>{gettext("No")}</span>;
    }

    private buildOfferRow(index: number, offer: IOffer) {
        const itemClasses = classNames({
            "offergroup__offer": true,
            "offergroup__offer--inactive": !offer.is_available,
        });
        return (
            <tr key={`offer-${offer.id}`} className={itemClasses}>
                <td className="offergroup__offer__index">
                    <a href={offer.details_link}>{index}</a>
                </td>
                <td className="offergroup__offer__name">
                    <a href={offer.details_link}>{offer.name}</a>
                </td>
                <td className="offergroup__offer__priority">
                    {offer.priority}
                </td>
                <td className="offergroup__offer__type">
                    <span className="label label-info">{gettext("Offer")}</span>
                </td>
            </tr>
        );
    }

    private buildVoucherRow(index: number, offer: IOffer) {
        const elems = offer.vouchers.map((voucher) => {
            const itemClasses = classNames({
                "offergroup__voucher": true,
                "offergroup__voucher--inactive": !voucher.is_active,
            });
            return (
                <tr key={`voucher-${voucher.id}`} className={itemClasses}>
                    <td className="offergroup__voucher__index">
                        <a href={voucher.details_link}>{index}</a>
                    </td>
                    <td className="offergroup__voucher__name">
                        <a href={voucher.details_link}>{voucher.name}</a>
                    </td>
                    <td className="offergroup__voucher__priority">
                        {offer.priority}
                    </td>
                    <td className="offergroup__voucher__type">
                        <span className="label label-success">
                            {gettext("Voucher")}
                        </span>
                    </td>
                </tr>
            );
        });
        return elems;
    }

    private buildOfferList(group: IOfferGroup) {
        const rows = group.offers
            .filter((offer) => {
                // Don't display voucher offers who's voucher has been deleted
                if (
                    offer.offer_type === "Voucher" &&
                    offer.vouchers.length <= 0
                ) {
                    return false;
                }
                return true;
            })
            .map((offer, i) => {
                const index = i + 1;
                return offer.vouchers.length > 0
                    ? this.buildVoucherRow(index, offer)
                    : this.buildOfferRow(index, offer);
            });
        return (
            <table className="table table-bordered table-striped offergroup-subtable">
                <caption>{group.name}</caption>
                <thead>
                    <tr>
                        <th className="offergroup__offer__index">
                            {gettext("#")}
                        </th>
                        <th className="offergroup__offer__name">
                            {gettext("Name")}
                        </th>
                        <th className="offergroup__offer__priority">
                            {gettext("Priority")}
                        </th>
                        <th className="offergroup__offer__type">
                            {gettext("Type")}
                        </th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        );
    }

    private buildGroupRows() {
        const numCols = 5;
        if (this.state.isLoading) {
            return (
                <tr>
                    <td colSpan={numCols} className="offergroup__empty">
                        {gettext("Loading…")}
                    </td>
                </tr>
            );
        }
        if (this.state.groups.length <= 0) {
            return (
                <tr>
                    <td colSpan={numCols} className="offergroup__empty">
                        {gettext("No Offer Groups found.")}
                    </td>
                </tr>
            );
        }
        return this.state.groups.map((group) => {
            return (
                <tr key={group.id} data-group-slug={group.slug}>
                    <td>{group.name}</td>
                    <td>{this.buildBooleanLabel(group.is_system_group)}</td>
                    <td>{group.priority}</td>
                    <td className="subtable-container">
                        {this.buildOfferList(group)}
                    </td>
                    <td>{this.buildGroupActions(group)}</td>
                </tr>
            );
        });
    }

    render() {
        return (
            <table className="table table-bordered">
                <caption>
                    <i className="fas fa-gift"></i>
                </caption>
                <tbody>
                    <tr>
                        <th>{gettext("Name")}</th>
                        <th>{gettext("Is System Group?")}</th>
                        <th>{gettext("Priority")}</th>
                        <th>{gettext("Group Contents")}</th>
                        <th>{gettext("Actions")}</th>
                    </tr>
                    {this.buildGroupRows()}
                </tbody>
            </table>
        );
    }
}

export default OfferGroupTable;
