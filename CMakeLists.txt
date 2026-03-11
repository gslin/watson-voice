cmake_minimum_required(VERSION 3.16)
project(fcitx5-watson-voice VERSION 0.1.0)

find_package(ECM 1.0.0 REQUIRED)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH} ${CMAKE_MODULE_PATH})

find_package(Fcitx5Core 5.0.0 REQUIRED)

# Addon shared library
add_library(watson-voice MODULE src/watson-voice.cpp)
target_link_libraries(watson-voice PRIVATE Fcitx5::Core)
set_target_properties(watson-voice PROPERTIES PREFIX "")

# Install addon library
install(TARGETS watson-voice DESTINATION "${FCITX_INSTALL_ADDONDIR}")

# Install addon metadata
install(FILES src/watson-voice-addon.conf
        RENAME watson-voice.conf
        DESTINATION "${FCITX_INSTALL_PKGDATADIR}/addon")

# Install input method metadata
install(FILES src/watson-voice-im.conf
        RENAME watson-voice.conf
        DESTINATION "${FCITX_INSTALL_PKGDATADIR}/inputmethod")
