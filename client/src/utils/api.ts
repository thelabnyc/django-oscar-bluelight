import request from 'superagent';
import {IOfferGroup} from './api.interfaces';


export const listOfferGroups = async (endpoint = '/dashboard/offers/api/offergroups/') => {
    const resp = await request
        .get(endpoint)
        .set('Accept', 'application/json');
    return resp.body as IOfferGroup[];
};
