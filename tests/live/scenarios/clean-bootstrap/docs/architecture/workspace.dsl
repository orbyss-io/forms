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
    }
}
