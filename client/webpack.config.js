const webpack = require('webpack');
const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');
const ExtractTextPlugin = require('extract-text-webpack-plugin');

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
        loader: 'babel-loader',
        query: {
            presets: ['es2015']
        }
    },
    {
        test: /\.scss$/,
        loader: ExtractTextPlugin.extract({
            use: ['css-loader', 'postcss-loader', 'sass-loader'],
        }),
        include: APP_DIR,
    },
    {
        test: /\.css$/,
        loader: ExtractTextPlugin.extract({
            use: ['css-loader'],
        }),
    },
];


// Transformation Plugins
let plugins = [
    new BundleTracker({
        path: BUILD_DIR,
        filename: 'webpack-stats.json'
    }),
    new webpack.optimize.CommonsChunkPlugin({
        name: 'vendor',
        minChunks: Infinity
    }),
    new webpack.DefinePlugin({
        'process.env':{
            'NODE_ENV': JSON.stringify(process.env.NODE_ENV)
        }
    }),
    new ExtractTextPlugin('[name].css'),
    new webpack.optimize.UglifyJsPlugin({
        compress: {
            warnings: false,
        },
        mangle: true,
        beautify: false,
        sourceMap: true,
    })
];


// Vendor Bundle
const vendorPackages = [
    'react-dom',
    'react',
    'superagent',
];


const config = {
    devtool: "source-map",
    resolve: {
        modules: ['node_modules'],
        extensions: [".webpack.js", ".web.js", ".ts", ".tsx", ".js"],
    },
    entry: {
        vendor: vendorPackages,
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
};

module.exports = config;
