import request = require('superagent');


export const listOfferGroups = function(endpoint = '/dashboard/offers/api/offergroups/', callback?: (err: any, resp: request.Response) => void) {
    return request
        .get(endpoint)
        .set('Accept', 'application/json')
        .end(callback);
};
