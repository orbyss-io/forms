workspace "Greeting CLI" "Program Kit C4-aligned intake model" {
    model {
        maintainer = person "Local maintainer" "Runs the greeting command locally." "ProgramKitId:maintainer,ProgramKitType:person,ProgramKitStatus:explicit"
        greeting_cli = softwareSystem "Greeting CLI" "Prints the exact Program Kit greeting and reports invalid arguments." "CommandLine,ProgramKitId:greeting-cli,ProgramKitType:software-system,ProgramKitStatus:explicit,ProgramKitOwner:Local maintainer"
        greeting_context = softwareSystem "Greeting" "Candidate boundary for the complete greeting journey." "Domain,ProgramKitId:greeting-context,ProgramKitType:bounded-context,ProgramKitStatus:proposed,ProgramKitOwner:Local maintainer"
        maintainer_invokes_cli = maintainer -> greeting_cli "Invokes the greeting command" "Local process" "ProgramKitId:maintainer-invokes-cli,ProgramKitStatus:explicit"
    }

    views {
        systemContext greeting_cli "system-context" {
            include maintainer greeting_cli
            autolayout lr
        }
        systemLandscape "domain-context" {
            include greeting_cli greeting_context
            autolayout lr
        }

        styles {
            element "Element" {
                shape RoundedBox
                background #F8FAFC
                color #172033
                stroke #94A3B8
                strokeWidth 2
                fontSize 22
            }
            element "Person" {
                shape Person
                background #0F766E
                color #FFFFFF
                stroke #115E59
                strokeWidth 2
            }
            element "Software System" {
                background #2563EB
                color #FFFFFF
                stroke #1D4ED8
                strokeWidth 2
            }
            element "ProgramKitType:bounded-context" {
                background #7C3AED
                color #FFFFFF
                stroke #6D28D9
                strokeWidth 2
            }
            element "ProgramKitStatus:proposed" {
                stroke #F97316
                border dashed
            }
            relationship "Relationship" {
                color #475569
                thickness 3
                style solid
                routing Orthogonal
                fontSize 18
            }
            relationship "ProgramKitStatus:proposed" {
                color #EA580C
                style dashed
            }
        }
    }
}
