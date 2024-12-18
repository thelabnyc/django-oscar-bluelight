export interface IVoucher {
    id: number;
    name: string;
    code: string;
    is_active: boolean;
    details_link: string;
}

export interface IOffer {
    id: number;
    name: string;
    offer_type: "Site" | "Voucher" | "User" | "Session";
    priority: number;
    is_available: boolean;
    vouchers: IVoucher[];
    details_link: string;
}

export interface IOfferGroup {
    id: number;
    name: string;
    slug: string;
    priority: number;
    is_system_group: boolean;
    offers: IOffer[];
    total_offers_count: number;
    update_link: string;
    delete_link: string;
}

export interface IOfferGroupWithPagination extends IOfferGroup {
    current_offers_page: number;
    has_more_offers: boolean;
}
