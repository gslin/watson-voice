#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/inputmethodengine.h>
#include <fcitx/inputpanel.h>
#include <fcitx/inputmethodmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/event.h>
#include <fcitx-utils/key.h>

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <cerrno>
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

std::string getResultFifoPath() {
    const char *runtime = std::getenv("XDG_RUNTIME_DIR");
    if (runtime) {
        return std::string(runtime) + "/watson-voice-result.fifo";
    }
    return "/tmp/watson-voice-result-" + std::to_string(getuid()) + ".fifo";
}

void sendCommand(const std::string &cmd) {
    int fd = open(getFifoPath().c_str(), O_WRONLY | O_NONBLOCK);
    if (fd < 0) {
        return;
    }
    std::string msg = cmd + "\n";
    (void)write(fd, msg.c_str(), msg.size());
    close(fd);
}

void ensureFifo(const std::string &path) {
    struct stat st;
    if (stat(path.c_str(), &st) == 0) {
        if (!S_ISFIFO(st.st_mode)) {
            unlink(path.c_str());
            mkfifo(path.c_str(), 0600);
        }
    } else {
        mkfifo(path.c_str(), 0600);
    }
}

bool isShiftSym(fcitx::KeySym sym) {
    return sym == FcitxKey_Shift_L || sym == FcitxKey_Shift_R;
}

bool isBareShiftKey(const fcitx::Key &key) {
    return isShiftSym(key.sym()) &&
           !key.states().unset(fcitx::KeyState::Shift)
                .testAny(fcitx::KeyState::SimpleMask);
}

} // anonymous namespace

class WatsonVoiceEngine : public fcitx::InputMethodEngineV2 {
public:
    WatsonVoiceEngine(fcitx::Instance *instance) : instance_(instance) {
        setupResultFifo();
    }

    ~WatsonVoiceEngine() {
        closeResultFifo();
    }

    void activate(const fcitx::InputMethodEntry & /*entry*/,
                  fcitx::InputContextEvent &event) override {
        clearPendingShift();
        lastIC_ = event.inputContext();
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
        clearPendingShift();
        sendCommand("stop");
        auto *ic = event.inputContext();
        ic->inputPanel().reset();
        ic->updateUserInterface(
            fcitx::UserInterfaceComponent::InputPanel);
    }

    void keyEvent(const fcitx::InputMethodEntry & /*entry*/,
                  fcitx::KeyEvent &keyEvent) override {
        const auto sym = keyEvent.rawKey().sym();

        if (pendingShift_) {
            if (keyEvent.isRelease() && sym == pendingShiftSym_) {
                clearPendingShift();
                sendCommand("segment");
                keyEvent.filterAndAccept();
                return;
            }
            clearPendingShift();
        }

        if (keyEvent.key().check(FcitxKey_Escape) && !keyEvent.isRelease()) {
            clearPendingShift();
            sendCommand("cancel");
            if (instance_->inputMethodManager().groupCount() > 0) {
                instance_->toggle();
            }
            keyEvent.filterAndAccept();
            return;
        }

        if (!keyEvent.isRelease() && isBareShiftKey(keyEvent.rawKey())) {
            pendingShift_ = true;
            pendingShiftSym_ = sym;
            return;
        }
    }

    void reset(const fcitx::InputMethodEntry & /*entry*/,
               fcitx::InputContextEvent &event) override {
        clearPendingShift();
        auto *ic = event.inputContext();
        ic->inputPanel().reset();
        ic->updateUserInterface(
            fcitx::UserInterfaceComponent::InputPanel);
    }

private:
    fcitx::Instance *instance_;
    fcitx::InputContext *lastIC_ = nullptr;
    int resultFd_ = -1;
    std::unique_ptr<fcitx::EventSourceIO> ioEvent_;
    std::string resultBuf_;
    bool pendingShift_ = false;
    fcitx::KeySym pendingShiftSym_ = FcitxKey_None;

    void clearPendingShift() {
        pendingShift_ = false;
        pendingShiftSym_ = FcitxKey_None;
    }

    void setupResultFifo() {
        auto path = getResultFifoPath();
        ensureFifo(path);

        // Open read end in non-blocking mode.
        // O_RDWR keeps the FIFO open even when no writer is connected.
        resultFd_ = open(path.c_str(), O_RDWR | O_NONBLOCK);
        if (resultFd_ < 0) {
            return;
        }

        ioEvent_ = instance_->eventLoop().addIOEvent(
            resultFd_, fcitx::IOEventFlag::In,
            [this](fcitx::EventSourceIO *, int fd,
                   fcitx::IOEventFlags flags) -> bool {
                if (flags & fcitx::IOEventFlag::In) {
                    onResultReady(fd);
                }
                return true;
            });
    }

    void onResultReady(int fd) {
        char buf[4096];
        for (;;) {
            ssize_t n = read(fd, buf, sizeof(buf));
            if (n <= 0) {
                break;
            }
            resultBuf_.append(buf, static_cast<size_t>(n));
        }

        // Process complete lines
        std::string::size_type pos;
        while ((pos = resultBuf_.find('\n')) != std::string::npos) {
            std::string line = resultBuf_.substr(0, pos);
            resultBuf_.erase(0, pos + 1);

            if (!line.empty() && lastIC_) {
                lastIC_->commitString(line);
            }
        }
    }

    void closeResultFifo() {
        ioEvent_.reset();
        if (resultFd_ >= 0) {
            close(resultFd_);
            resultFd_ = -1;
        }
        auto path = getResultFifoPath();
        unlink(path.c_str());
    }
};

class WatsonVoiceFactory : public fcitx::AddonFactory {
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override {
        return new WatsonVoiceEngine(manager->instance());
    }
};

FCITX_ADDON_FACTORY(WatsonVoiceFactory);
