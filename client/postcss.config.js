module.exports = {
    plugins: [
        require('autoprefixer')({
            browsers: [
                "defaults",
                "last 2 versions",
                "IE 11",
                "last 5 ios_saf versions",
            ]
        }),
        require('cssnano')({
            preset: 'default',
        }),
    ],
};
