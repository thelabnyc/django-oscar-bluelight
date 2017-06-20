import React = require('react');
import classNames = require('classnames');
import {listOfferGroups} from '../utils/api';
import {IOfferGroup, IOffer} from '../utils/api.interfaces';

import './OfferGroupTable.scss';


export interface IProps {
    endpoint: string;
}


export interface IState {
    groups: IOfferGroup[];
}


class OfferGroupTable extends React.Component<IProps, IState> {
    constructor (props: IProps) {
        super(props);
        this.state = {
            groups: [],
        };
    }


    componentDidMount () {
        listOfferGroups(this.props.endpoint, (err, resp) => {
            if (err) {
                console.log(err);
                console.log(resp);
                return;
            }

            const groups = resp.body as IOfferGroup[];
            this.setState({
                groups: groups,
            });
        });
    }


    buildGroupActions (group: IOfferGroup) {
        const deleteClass = group.offers.length > 0 ? 'disabled' : '';
        const deleteTitle = group.offers.length > 0 ? 'Remove all offers from this group to delete it' : `Delete the ${group.name} offer group`;
        return (
            <div className="btn-toolbar">
                <div className="btn-group">
                    <button className="btn btn-default dropdown-toggle" type="button" data-toggle="dropdown" aria-expanded="true">
                        Actions <span className="caret"></span>
                    </button>
                    <ul className="dropdown-menu pull-right">
                        <li>
                            <a href={group.update_link} title={`Edit the details of the ${group.name} offer group`}>Edit</a>
                        </li>
                        <li className={deleteClass} title={deleteTitle}>
                            <a href={group.delete_link}>Delete</a>
                        </li>
                    </ul>
                </div>
            </div>
        );
    }


    buildOfferListItem (offer: IOffer) {
        if (!offer.vouchers.length) {
            const itemClasses = classNames({
                'offergroup__offer': true,
                'offergroup__offer--inactive': !offer.is_available,
            });
            return (
                <li key={`offer-${offer.id}`} className={itemClasses}>
                    <a href={offer.details_link}>{offer.name} (priority {offer.priority})</a>
                    <span className="label label-info">Offer</span>
                </li>
            );
        }

        return offer.vouchers.map((voucher) => {
            const itemClasses = classNames({
                'offergroup__voucher': true,
                'offergroup__voucher--inactive': !voucher.is_active,
            });
            return (
                <li key={`voucher-${voucher.id}`} className={itemClasses}>
                    <a href={voucher.details_link}>{voucher.name} (priority {offer.priority})</a>
                    <span className="label label-success">Voucher</span>
                </li>
            );
        });
    }


    buildOfferList (group: IOfferGroup) {
        const self = this;

        const rows = group.offers.map((offer) => {
            return self.buildOfferListItem(offer);
        });

        return (
           <ol>{rows}</ol>
        );
    }


    buildGroupRows () {
        const self = this;

        if (this.state.groups.length <= 0) {
            return (
                <tr>
                    <td colSpan={4} className="offergroup__empty">No Offer Groups found.</td>
                </tr>
            );
        }

        return this.state.groups.map((group) => {
            return (
                <tr key={group.id}>
                    <td>{group.name}</td>
                    <td>{group.priority}</td>
                    <td>{self.buildOfferList(group)}</td>
                    <td>{self.buildGroupActions(group)}</td>
                </tr>
            );
        });
    }


    render () {
        return (
            <table className="table table-striped table-bordered">
                <caption>
                    <i className="icon-gift icon-large"></i>
                </caption>
                <tbody>
                    <tr>
                        <th>Name</th>
                        <th>Priority</th>
                        <th>Contains Offers</th>
                        <th>Actions</th>
                    </tr>
                    {this.buildGroupRows()}
                </tbody>
            </table>
        );
    }
}

export default OfferGroupTable;
