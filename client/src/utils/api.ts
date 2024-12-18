import request from "superagent";
import { IOfferGroup, IOfferGroupWithPagination } from "./api.interfaces";

export const listOfferGroups = async (
    endpoint = "/dashboard/offers/api/offergroups/",
    offersPage = 1,
) => {
    const offersPageSize = 200;
    const resp = await request
        .get(endpoint)
        .query({ offers_page: offersPage, offers_page_size: offersPageSize })
        .set("Accept", "application/json");

    const groups = resp.body as IOfferGroup[];
    // Add pagination info to response
    return groups.map(
        (group): IOfferGroupWithPagination => ({
            ...group,
            current_offers_page: offersPage,
            has_more_offers:
                group.total_offers_count > offersPage * offersPageSize,
        }),
    );
};
