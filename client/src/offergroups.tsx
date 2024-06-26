import "core-js/stable";
import "regenerator-runtime/runtime";
import React from "react";
import { createRoot } from "react-dom/client";
import OfferGroupTable from "./offergroups/OfferGroupTable";

type INamedInterpolationData = { [key: string]: string };
type IPositionalInterpolationData = string[];
type IInterpolationData =
    | INamedInterpolationData
    | IPositionalInterpolationData;
interface IDjango {
    readonly gettext: (msgid: string) => string;
    readonly ngettext: (
        singular: string,
        plural: string,
        count: number,
    ) => string;
    readonly gettext_noop: (msgid: string) => string;
    readonly pgettext: (context: string, msgid: string) => string;
    readonly npgettext: (
        context: string,
        singular: string,
        plural: string,
        count: number,
    ) => string;
    readonly interpolate: (
        fmt: string,
        obj: IInterpolationData,
        named?: boolean,
    ) => string;

    readonly pluralidx: (count: number) => number;

    readonly jsi18n_initialized: boolean;
    readonly catalog: {
        [msgid: string]: string;
    };
    readonly formats: {
        [msgid: string]: string | string[];
    };
    readonly get_format: (formatType: string) => string | string[];
}

declare global {
    // Django i18n functions
    const django: IDjango;
    const pluralidx: IDjango["pluralidx"];
    const gettext: IDjango["gettext"];
    const ngettext: IDjango["ngettext"];
    const gettext_noop: IDjango["gettext_noop"];
    const pgettext: IDjango["pgettext"];
    const npgettext: IDjango["npgettext"];
    const interpolate: IDjango["interpolate"];
    const get_format: IDjango["get_format"];
}

const main = function () {
    const elem = document.querySelector<HTMLDivElement>("#offergroup-table")!;
    const root = createRoot(elem);
    root.render(
        <OfferGroupTable endpoint={elem.dataset.offergroupApi || ""} />,
    );
};

main();
