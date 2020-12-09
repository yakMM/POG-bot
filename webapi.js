registerPlugin({
    name: 'Extended SinusBot API',
    version: '1',
    description: 'Extended SinusBot API',
    author: 'Edited by Monkeydg. Original fork by Andreas <andreas@andreasfink.xyz> from the repo by mxschmitt <max@schmitt.mx> & irgendwer <dev@sandstorm-projects.de>',
    backends: ['ts3', 'discord'],
    requiredModules: [],
    vars: [{
            name: 'debug',
            title: 'enable debug (default deactivated)',
            type: 'select',
            options: ['on', 'off']
        }, {
            name: 'play',
            title: 'enable playing (default activated)',
            type: 'select',
            options: ['on', 'off']
        }, {
            name: 'dl',
            title: 'enable downloading (default activated)',
            type: 'select',
            options: ['on', 'off']
        }, {
            name: 'enq',
            title: 'enable enqueuing (default activated)',
            type: 'select',
            options: ['on', 'off']
        },
        {
            name: 'move',
            title: 'enable moving (default activated)',
            type: 'select',
            options: ['on', 'off']
        }
    ]
}, (_, config) => {
    const errorMessages = {
        NoPermission: "Do you have enough permissions for this action?",
        DLDisabled: "Downloading is not enabled.",
        EQDisabled: "Enqueuing is not enabled.",
        PlayDisabled: "Playing is not enabled."
    };
    const engine = require('engine');
    const backend = require('backend');
    const store = require('store');
    const event = require('event');
    const media = require('media');
    const http = require('http');
    const format = require('format');

    engine.log("Sinusbot ExtendedAPI");


    event.on('api:ytplay', ev => {
        const res = new Response();
        // Check for PRIV_PLAYBACK
        if (!ev.user() || !ev.user().privileges || (ev.user().privileges() & 0x1000) == 0) {
            res.setError(errorMessages.NoPermission);
            return res.getData();
        }
        if (config.play != 1) {
            media.yt(ev.data());
            if (config.debug == 1) {
                engine.log(`YTWeb Triggered with "played" at ${ev.data()}`);
            }
            res.setData("The Video will be sucessfully played now.");
            return res.getData();
        } else {
            if (config.debug == 1) {
                engine.log(`YTWeb tried to play ${ev.data()} but it was deactivated.`);
            }
            res.setError(errorMessages.PlayDisabled);
            return res.getData();
        }
    });

    event.on('api:ytenq', ev => {
        const res = new Response();
        // Check for PRIV_ENQUEUE
        if (!ev.user() || !ev.user().privileges || (ev.user().privileges() & 0x2000) == 0) {
            res.setError(errorMessages.NoPermission);
            return res.getData();
        }
        if (config.enq != 1) {
            media.enqueueYt(ev.data());
            if (config.debug == 1) {
                engine.log(`YTWeb Triggered with "enque" at ${ev.data()}`);
            }
            res.setData("The Video will be sucessfully enqueued now.");
            return res.getData();
        } else {
            if (config.debug == 1) {
                engine.log(`YTWeb tried to play ${ev.data()} but it was deactivated.`);
            }
            res.setError(errorMessages.EQDisabled);
            return res.getData();
        }
    });

    event.on('api:ytdl', ev => {
        const res = new Response();
        // Check for PRIV_UPLOAD_FILE
        if (!ev.user || !ev.user().privileges || (ev.user().privileges() & 0x4) == 0) {
            res.setError(errorMessages.NoPermission);
            return res.getData();
        }
        if (config.dl != 1) {
            media.ytdl(ev.data(), false);
            if (config.debug == 1) {
                engine.log(`YTWeb Triggered with "downloaded" at ${ev.data()}`);
            }
            res.setData("The Video will be sucessfully downloaded now.");
            return res.getData();
        } else {
            if (config.debug == 1) {
                engine.log(`YTWeb tried to download ${ev.data()} but it was deactivated.`);
            }
            res.setError(errorMessages.DLDisabled);
            return res.getData();
        }
    });

    event.on('api:move', ev => {
        const res = new Response();
        // Check for EDIT_BOT_SETTINGS
        if (!ev.user || !ev.user().privileges || (ev.user().privileges() & (1 << 16)) == 0) {
            res.setError(errorMessages.NoPermission);
            return res.getData();
        }
        if (config.move != 1) {
            console.log(ev.data())
            const move = backend.getBotClient().moveTo(ev.data().id, ev.data().password);
            console.log(move);
            engine.log(`Move Triggered with id: ${ev.data().id} and password: ${ev.data().password}`);
            res.setData("The bot has moved his channel.");
            return res.getData();
        } else {
            if (config.debug == 1) {
                engine.log(`YTWeb tried to download ${ev.data()} but it was deactivated.`);
            }
            res.setError(errorMessages.DLDisabled);
            return res.getData();
        }
    });



    class Response {
        constructor() {
            this.success = true;
            this.data = null;
        }
        setData(data) {
            this.data = data;
        }
        getData() {
            return {
                data: this.data,
                success: this.success
            }
        }
        setError(error) {
            this.success = false;
            this.data = error;
        };
    }

    function getGetParameter(url, name) {
        name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
        const regexS = `[\\?&]${name}=([^&#]*)`;
        const regex = new RegExp(regexS);
        const results = regex.exec(url);
        return results == null ? null : results[1];
    }
});
