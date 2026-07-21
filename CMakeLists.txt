cmake_minimum_required(VERSION 3.15)

project(ObsidianB7000 VERSION 0.5.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "Minimum macOS deployment version")

enable_testing()

if (MSVC)
    set(PEDAL_WARNING_FLAGS /W4)
else()
    set(PEDAL_WARNING_FLAGS -Wall -Wextra)
endif()

add_subdirectory(libs/JUCE)
add_subdirectory(libs/xsimd)
add_subdirectory(libs/chowdsp_wdf)

get_target_property(_chowdsp_inc chowdsp_wdf INTERFACE_INCLUDE_DIRECTORIES)
set_target_properties(chowdsp_wdf PROPERTIES INTERFACE_SYSTEM_INCLUDE_DIRECTORIES "${_chowdsp_inc}")

juce_add_plugin(ObsidianB7000
    COMPANY_NAME "Leigh Pierce"
    BUNDLE_ID com.leighpierce.obsidianb7000
    PLUGIN_MANUFACTURER_CODE LPrc
    PLUGIN_CODE Ob7k
    FORMATS AU VST3
    PRODUCT_NAME "Obsidian B7000"
    COPY_PLUGIN_AFTER_BUILD TRUE
)

juce_add_binary_data(ObsidianB7000Assets
    SOURCES
        ui/b7k_texture_base.png
        ui/T_Knob.png
        ui/Footswitch_up.png
        ui/footswitch_down.png
        ui/blue_led_on.png
        ui/blue_led_off.png
        ui/switch_up.png
        ui/switch_Mid.png
        ui/switch_down.png
        ui/vol_trim.png
        ui/LexendExa-Regular.ttf
        ui/LexendExa-Bold.ttf
)

target_sources(ObsidianB7000
    PRIVATE
        src/PluginProcessor.cpp
        src/PluginEditor.cpp
        src/ui/PedalLookAndFeel.cpp
        src/ui/PedalFace.cpp
        src/dsp/PedalDSP.h
)

target_compile_definitions(ObsidianB7000
    PUBLIC
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_VST3_CAN_REPLACE_VST2=0
)

target_link_libraries(ObsidianB7000
    PRIVATE
        juce::juce_audio_utils
        juce::juce_dsp
        chowdsp::chowdsp_wdf
        xsimd
        ObsidianB7000Assets
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags
)

target_compile_options(ObsidianB7000 PRIVATE ${PEDAL_WARNING_FLAGS})

# Tests
add_executable(DummyTest tests/DummyTest.cpp)
target_compile_options(DummyTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME DummyTest COMMAND DummyTest)

add_executable(RCLowpassTest tests/RCLowpassTest.cpp)
target_link_libraries(RCLowpassTest PRIVATE chowdsp::chowdsp_wdf)
target_compile_options(RCLowpassTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME RCLowpassTest COMMAND RCLowpassTest)

# Phase 4 — stage-by-stage linear DSP tests
add_executable(InputBufferTest tests/InputBufferTest.cpp)
target_link_libraries(InputBufferTest PRIVATE chowdsp::chowdsp_wdf)
target_compile_options(InputBufferTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME InputBufferTest COMMAND InputBufferTest)

add_executable(TrebleAttackTest tests/TrebleAttackTest.cpp)
target_compile_options(TrebleAttackTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME TrebleAttackTest COMMAND TrebleAttackTest)

add_executable(DriveStageTest tests/DriveStageTest.cpp)
target_compile_options(DriveStageTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME DriveStageTest COMMAND DriveStageTest)

add_executable(RecoveryBridgedTTest tests/RecoveryBridgedTTest.cpp)
target_compile_options(RecoveryBridgedTTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME RecoveryBridgedTTest COMMAND RecoveryBridgedTTest)

add_executable(SallenKeyLPFTest tests/SallenKeyLPFTest.cpp)
target_compile_options(SallenKeyLPFTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME SallenKeyLPFTest COMMAND SallenKeyLPFTest)

add_executable(LevelBlendTest tests/LevelBlendTest.cpp)
target_compile_options(LevelBlendTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME LevelBlendTest COMMAND LevelBlendTest)

add_executable(MidBandTest tests/MidBandTest.cpp)
target_compile_options(MidBandTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME MidBandTest COMMAND MidBandTest)

add_executable(BaxandallTest tests/BaxandallTest.cpp)
target_compile_options(BaxandallTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME BaxandallTest COMMAND BaxandallTest)

add_executable(EqPreGainTest tests/EqPreGainTest.cpp)
target_compile_options(EqPreGainTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME EqPreGainTest COMMAND EqPreGainTest)

add_executable(MasterOutTest tests/MasterOutTest.cpp)
target_compile_options(MasterOutTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME MasterOutTest COMMAND MasterOutTest)

add_executable(JfetStageTest tests/JfetStageTest.cpp)
target_compile_options(JfetStageTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME JfetStageTest COMMAND JfetStageTest)

add_executable(ClipperTest tests/ClipperTest.cpp)
target_compile_options(ClipperTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME ClipperTest COMMAND ClipperTest)

add_executable(PedalChainTest tests/PedalChainTest.cpp)
target_link_libraries(PedalChainTest PRIVATE chowdsp::chowdsp_wdf)
target_compile_options(PedalChainTest PRIVATE ${PEDAL_WARNING_FLAGS})
add_test(NAME PedalChainTest COMMAND PedalChainTest)

# Phase-7 calibration harness: render a WAV through the real chain from the CLI.
# Mirrors PluginProcessor::processBlock (see the header comment in the source);
# needs juce_audio_formats for 32-bit-float WAV I/O and juce_dsp for the
# oversampler. NOT registered with add_test() — it's a tool, not a pass/fail gate.
juce_add_console_app(OfflineRender)
target_sources(OfflineRender PRIVATE analysis/offline_render.cpp)
target_link_libraries(OfflineRender
    PRIVATE
        juce::juce_audio_formats
        juce::juce_dsp
        chowdsp::chowdsp_wdf
        xsimd
    PUBLIC
        juce::juce_recommended_config_flags)
target_compile_definitions(OfflineRender PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
target_compile_options(OfflineRender PRIVATE ${PEDAL_WARNING_FLAGS})

# Oversampling + delay-comp validation (needs JUCE dsp + FFT)
juce_add_console_app(OSValidationTest)
target_sources(OSValidationTest PRIVATE tests/OSValidationTest.cpp)
target_link_libraries(OSValidationTest
    PRIVATE
        juce::juce_dsp
        chowdsp::chowdsp_wdf
        xsimd
    PUBLIC
        juce::juce_recommended_config_flags)
add_test(NAME OSValidationTest COMMAND OSValidationTest)

# Headless editor snapshot tool (build.md "UI changes" testing pattern) — renders the real
# editor off-screen at min/default/max UI scale to PNGs for visual review. NOT registered with
# add_test() — it's a visual-inspection tool, not a pass/fail gate.
juce_add_console_app(EditorSnapshot)
target_sources(EditorSnapshot PRIVATE tests/EditorSnapshot.cpp)
target_link_libraries(EditorSnapshot
    PRIVATE
        ObsidianB7000
        juce::juce_gui_extra
        juce::juce_dsp
        chowdsp::chowdsp_wdf
        xsimd
    PUBLIC
        juce::juce_recommended_config_flags)
target_compile_definitions(EditorSnapshot PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
target_compile_options(EditorSnapshot PRIVATE ${PEDAL_WARNING_FLAGS})
