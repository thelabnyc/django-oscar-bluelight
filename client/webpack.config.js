const webpack = require('webpack');
const path = require('path');
const fs = require('fs');
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const BUILD_DIR = path.resolve(__dirname, '../server/src/oscarbluelight/static/oscarbluelight/');
const APP_DIR = path.resolve(__dirname, './src/');
const IS_PROD = (process.env.NODE_ENV === 'production');


// Rules
const rules = [
    {
        test: /\.tsx?$/,
        include: APP_DIR,
        loader: 'awesome-typescript-loader',
        enforce: 'pre',
    },
    {
        enforce: "pre",
        test: /\.js$/,
        loader: "source-map-loader",
    },
    {
        test: /\.[tj]sx?/,
        include: APP_DIR,
        use: {
            loader: 'babel-loader',
            options: Object.assign({}, JSON.parse(fs.readFileSync('.babelrc', 'utf8')), {
                cacheDirectory: true,
            }),
        }
    },
    {
        test: /\.scss$/,
        include: APP_DIR,
        use: [
            MiniCssExtractPlugin.loader,
            {
                loader: 'css-loader',
            },
            {
                loader: 'postcss-loader',
            },
            {
                loader: 'sass-loader',
            },
        ],
    },
    {
        test: /\.css$/,
        include: APP_DIR,
        use: [
            MiniCssExtractPlugin.loader,
            {
                loader: 'css-loader',
            },
        ],
    },
];


// Transformation Plugins
let plugins = [
    new BundleTracker({
        path: BUILD_DIR,
        filename: 'webpack-stats.json'
    }),
    new webpack.DefinePlugin({
        'process.env':{
            'NODE_ENV': JSON.stringify(process.env.NODE_ENV)
        }
    }),
    new MiniCssExtractPlugin({
        filename: "[name].css",
        chunkFilename: "[id].css"
    }),
];


const config = {
    mode: IS_PROD ? 'production' : 'development',
    devtool: "source-map",
    resolve: {
        modules: ['node_modules'],
        extensions: [".webpack.js", ".web.js", ".ts", ".tsx", ".js"],
    },
    entry: {
        offergroups: path.join(APP_DIR, 'offergroups.tsx'),
    },
    output: {
        path: BUILD_DIR,
        filename: '[name].js'
    },
    plugins: plugins,
    module: {
        rules: rules
    },
    optimization: {
        splitChunks: {
            cacheGroups: {
                commons: {
                    test: /[\\/]node_modules[\\/]/,
                    name: "vendor",
                    chunks: "all",
                },
            },
        },
    },
};

module.exports = config;
