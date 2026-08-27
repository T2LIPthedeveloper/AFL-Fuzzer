package com.aflfuzzer.spring.api;

import com.aflfuzzer.spring.campaign.CampaignService;
import com.aflfuzzer.spring.energy.DeviceCampaignService;
import com.aflfuzzer.spring.model.CampaignRequest;
import com.aflfuzzer.spring.model.CampaignStatus;
import com.aflfuzzer.spring.model.MutationRequest;
import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.mutation.MutationEngine;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class CampaignController {
    private final CampaignService campaignService;
    private final MutationEngine mutationEngine;
    private final DeviceCampaignService deviceCampaignService;

    public CampaignController(
            CampaignService campaignService,
            MutationEngine mutationEngine,
            DeviceCampaignService deviceCampaignService
    ) {
        this.campaignService = campaignService;
        this.mutationEngine = mutationEngine;
        this.deviceCampaignService = deviceCampaignService;
    }

    @GetMapping("/health")
    public MapHealth health() {
        return new MapHealth("UP", "spring-fuzzer");
    }

    @PostMapping("/campaigns")
    public CampaignStatus start(@Valid @RequestBody CampaignRequest request) {
        return campaignService.start(request);
    }

    @GetMapping("/campaigns/{id}")
    public CampaignStatus get(@PathVariable String id) {
        CampaignStatus status = campaignService.get(id);
        if (status == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Campaign not found");
        }
        return status;
    }

    @GetMapping(value = "/campaigns/{id}/report", produces = MediaType.TEXT_HTML_VALUE)
    public String report(@PathVariable String id) {
        String html = campaignService.report(id);
        if (html == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Report not found");
        }
        return html;
    }

    @PostMapping("/mutations")
    public SeedPayload mutate(@Valid @RequestBody MutationRequest request) {
        return mutationEngine.mutate(request.getSeed(), request.getCount());
    }

    @PostMapping("/device-campaigns")
    public DeviceCampaignService.DeviceResult device(
            @RequestBody(required = false) List<String> seeds,
            @RequestParam(defaultValue = "5") int rounds
    ) {
        return deviceCampaignService.run(seeds == null ? List.of() : seeds, rounds);
    }

    public record MapHealth(String status, String service) {}
}
