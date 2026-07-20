cmake_minimum_required(VERSION 3.15)

project(ObsidianB7000 VERSION 0.2.3)

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
