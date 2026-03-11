#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/inputmethodengine.h>
#include <fcitx/inputpanel.h>
#include <fcitx/inputmethodmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/key.h>

#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>
#include <cstdlib>
#include <string>

namespace {

std::string getFifoPath() {
    const char *runtime = std::getenv("XDG_RUNTIME_DIR");
    if (runtime) {
        return std::string(runtime) + "/watson-voice.fifo";
    }
    return "/tmp/watson-voice-" + std::to_string(getuid()) + ".fifo";
}

void sendCommand(const std::string &cmd) {
    int fd = open(getFifoPath().c_str(), O_WRONLY | O_NONBLOCK);
    if (fd < 0) {
        return;
    }
    std::string msg = cmd + "\n";
    // Best-effort write; ignore errors (daemon may not be running)
    (void)write(fd, msg.c_str(), msg.size());
    close(fd);
}

} // anonymous namespace

class WatsonVoiceEngine : public fcitx::InputMethodEngineV2 {
public:
    WatsonVoiceEngine(fcitx::Instance *instance) : instance_(instance) {}

    void activate(const fcitx::InputMethodEntry & /*entry*/,
                  fcitx::InputContextEvent &event) override {
        sendCommand("start");
        auto *ic = event.inputContext();
        ic->inputPanel().setAuxUp(
            fcitx::Text("\xf0\x9f\x8e\xa4 \xe9\x8c\x84\xe9\x9f\xb3\xe4"
                        "\xb8\xad\xe2\x80\xa6"));  // "🎤 錄音中…"
        ic->updateUserInterface(
            fcitx::UserInterfaceComponent::InputPanel);
    }

    void deactivate(const fcitx::InputMethodEntry & /*entry*/,
                    fcitx::InputContextEvent &event) override {
        sendCommand("stop");
        auto *ic = event.inputContext();
        ic->inputPanel().reset();
        ic->updateUserInterface(
            fcitx::UserInterfaceComponent::InputPanel);
    }

    void keyEvent(const fcitx::InputMethodEntry & /*entry*/,
                  fcitx::KeyEvent &keyEvent) override {
        if (keyEvent.key().check(FcitxKey_Escape) && !keyEvent.isRelease()) {
            sendCommand("cancel");
            // Switch back to previous input method
            if (instance_->inputMethodManager().groupCount() > 0) {
                instance_->toggle();
            }
            keyEvent.filterAndAccept();
            return;
        }
        // All other keys pass through to the application
    }

    void reset(const fcitx::InputMethodEntry & /*entry*/,
               fcitx::InputContextEvent &event) override {
        auto *ic = event.inputContext();
        ic->inputPanel().reset();
        ic->updateUserInterface(
            fcitx::UserInterfaceComponent::InputPanel);
    }

private:
    fcitx::Instance *instance_;
};

class WatsonVoiceFactory : public fcitx::AddonFactory {
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override {
        return new WatsonVoiceEngine(manager->instance());
    }
};

FCITX_ADDON_FACTORY(WatsonVoiceFactory);
